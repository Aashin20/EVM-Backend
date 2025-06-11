from core.db import Database
from models.evm import FLCRecord, FLCBallotUnit, EVMComponentType, EVMComponent,PairingRecord
from models.logs import FLCBallotUnitLogs,FLCRecordLogs
from pydantic import BaseModel
from models.logs import FLCBallotUnitLogs,FLCRecordLogs,EVMComponentLogs,PairingRecordLogs
from fastapi import HTTPException
from typing import Optional, List
from fastapi import Response


class FLCCUModel(BaseModel):
    cu_serial: str
    dmm_serial: str
    dmm_seal_serial: str
    pink_paper_seal_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None
    

class FLCBUModel(BaseModel):
    bu_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None



def flc_cu(data_list: List[FLCCUModel], user_id: int):
    with Database.get_session() as session:
        for data in data_list:
            cu = session.query(EVMComponent).filter_by(serial_number=data.cu_serial).first()
            dmm = session.query(EVMComponent).filter_by(serial_number=data.dmm_serial).first()

            if not all([cu, dmm]):
                raise HTTPException(status_code=404, detail=f"CU or DMM not found for CU serial {data.cu_serial} or DMM serial {data.dmm_serial}")

            if cu.component_type != EVMComponentType.CU or dmm.component_type != EVMComponentType.DMM:
                raise HTTPException(status_code=400, detail=f"Component types are incorrect for CU serial {data.cu_serial} or DMM serial {data.dmm_serial}")

            dmm_seal = session.query(EVMComponent).filter_by(serial_number=data.dmm_seal_serial).first()
            if not dmm_seal:
                dmm_seal = EVMComponent(
                    serial_number=data.dmm_seal_serial,
                    component_type=EVMComponentType.DMM_SEAL,
                    status="FLC_Passed" if data.passed else "FLC_Failed",
                    is_verified=True,
                    box_no=data.box_no
                )
                session.add(dmm_seal)
                session.flush()

            pink_paper_seal = session.query(EVMComponent).filter_by(serial_number=data.pink_paper_seal_serial).first()
            if not pink_paper_seal:
                pink_paper_seal = EVMComponent(
                    serial_number=data.pink_paper_seal_serial,
                    component_type=EVMComponentType.PINK_PAPER_SEAL,
                    status="FLC_Passed" if data.passed else "FLC_Failed",
                    is_verified=True,
                    box_no=data.box_no
                )
                session.add(pink_paper_seal)
                session.flush()

            flc = FLCRecord(
                cu_id=cu.id,
                dmm_id=dmm.id,
                dmm_seal_id=dmm_seal.id,
                pink_paper_seal_id=pink_paper_seal.id,
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            session.add(flc)
            
            pairing = PairingRecord(created_by_id=user_id)
            session.add(pairing)
            session.flush()

            # Update all components
            cu.pairing_id = pairing.id
            cu.box_no = data.box_no
            dmm.box_no = data.box_no
            dmm.pairing_id = pairing.id
            dmm_seal.pairing_id = pairing.id
            pink_paper_seal.pairing_id = pairing.id
            
            if data.passed:
                cu.status = "FLC_Passed"
                dmm.status = "FLC_Passed"
            else:
                cu.status = "FLC_Failed"
                dmm.status = "FLC_Failed"

        session.commit()
        
        # CREATE LOGS - Add corresponding entries to logs tables
        for data in data_list:
            # Get updated components
            cu = session.query(EVMComponent).filter_by(serial_number=data.cu_serial).first()
            dmm = session.query(EVMComponent).filter_by(serial_number=data.dmm_serial).first()
            dmm_seal = session.query(EVMComponent).filter_by(serial_number=data.dmm_seal_serial).first()
            pink_paper_seal = session.query(EVMComponent).filter_by(serial_number=data.pink_paper_seal_serial).first()
            
            # Create PairingRecordLogs
            pairing_log = PairingRecordLogs(
                evm_id=cu.pairing.evm_id if cu.pairing else None,
                polling_station_id=cu.pairing.polling_station_id if cu.pairing else None,
                created_by_id=user_id,
                completed_by_id=cu.pairing.completed_by_id if cu.pairing else None,
                completed_at=cu.pairing.completed_at if cu.pairing else None
            )
            session.add(pairing_log)
            session.commit()
            session.refresh(pairing_log)
            
            # Create EVMComponentLogs for all components
            components_to_log = [cu, dmm, dmm_seal, pink_paper_seal]
            component_log_ids = []
            
            for comp in components_to_log:
                comp_log = EVMComponentLogs(
                    serial_number=comp.serial_number,
                    component_type=comp.component_type,
                    status=comp.status,
                    is_verified=comp.is_verified,
                    dom=comp.dom,
                    box_no=comp.box_no,
                    current_user_id=comp.current_user_id,
                    current_warehouse_id=comp.current_warehouse_id,
                    pairing_id=pairing_log.id
                )
                session.add(comp_log)
                session.commit()
                session.refresh(comp_log)
                component_log_ids.append(comp_log.id)
            
            # Create FLCRecordLogs
            flc_log = FLCRecordLogs(
                cu_id=component_log_ids[0],  # CU log id
                dmm_id=component_log_ids[1],  # DMM log id
                dmm_seal_id=component_log_ids[2],  # DMM_SEAL log id
                pink_paper_seal_id=component_log_ids[3],  # PINK_PAPER_SEAL log id
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            session.add(flc_log)
        
        session.commit()
    
    return Response(status_code=200)



def flc_bu(datas: list[FLCBUModel],user_id: int):
    with Database.get_session() as session:
        for data in datas:
            bu = session.query(EVMComponent).filter_by(serial_number=data.bu_serial).first()
            if not bu:
                raise HTTPException(status_code=404, detail=f"Component with serial number {data.bu_serial} not found")
            
            # Create FLC record
            flc = FLCBallotUnit(
                bu_id=bu.id,
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            session.add(flc)
            
            # Update component
            bu.box_no = data.box_no
            if data.passed:
                bu.status = "FLC_Passed"
            else:
                bu.status = "FLC_Failed"
        
        session.commit()
        
        # CREATE LOGS - Add corresponding entries to logs tables
        for data in datas:
            bu = session.query(EVMComponent).filter_by(serial_number=data.bu_serial).first()
            
            # Create EVMComponentLogs entry (current state after update)
            component_log = EVMComponentLogs(
                serial_number=bu.serial_number,
                component_type=bu.component_type,
                status=bu.status,
                is_verified=bu.is_verified,
                dom=bu.dom,
                box_no=bu.box_no,
                current_user_id=bu.current_user_id,
                current_warehouse_id=bu.current_warehouse_id,
                pairing_id=bu.pairing_id
            )
            session.add(component_log)
            session.commit()
            session.refresh(component_log)
            
            # Create FLCBallotUnitLogs entry
            flc_log = FLCBallotUnitLogs(
                bu_id=component_log.id,  # Reference to the component log
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            session.add(flc_log)
        
        session.commit()
    
    return Response(status_code=200)
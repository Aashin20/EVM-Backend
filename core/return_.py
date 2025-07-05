from typing import List
from core.db import Database
from models.evm import EVMComponent, PairingRecord,PollingStation,FLCRecord,FLCBallotUnit
from models.logs import PairingRecordLogs,EVMComponentLogs,FLCBallotUnitLogs,FLCRecordLogs
from fastapi import Response,HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from models.users import User


class DecommissionModel(BaseModel):
    local_body_id: str
    evm_ids: List[str]

def status_change(local_body: str,status: str):
    if status not in ["polling","polled","counted"]:
        raise HTTPException(status_code=204)
    elif status == "polled":
        current_status = "polling"
    elif status == "counted":
        current_status = "polled"
    with Database.get_session() as session:
        evm_components = (
            session.query(EVMComponent)
            .join(PairingRecord, EVMComponent.pairing_id == PairingRecord.id)
            .join(PollingStation, PairingRecord.polling_station_id == PollingStation.id)
            .filter(PollingStation.local_body_id == local_body)
            .filter(PollingStation.status == "approved")
            .filter(EVMComponent.status == current_status)
        )
        
        for component in evm_components:
            component.status = status
        
        session.commit()
        return Response(status_code=200)


def decommission_evms(data: DecommissionModel):
    with Database.get_session() as session:
        try:
            # Get all pairings
            pairings = (
                session.query(PairingRecord)
                .join(PollingStation)
                .filter(PollingStation.local_body_id == data.local_body_id)
                .filter(PairingRecord.evm_id.in_(data.evm_ids))
                .all()
            )
            
            if not pairings:
                raise HTTPException(status_code=404, detail="No EVMs found")
            
            if len(pairings) != len(data.evm_ids):
                raise HTTPException(status_code=404, detail="Some EVMs not found")
            
            # First validate ALL EVMs are eligible
            for pairing in pairings:
                cu = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id,
                    EVMComponent.component_type == "CU"
                ).first()
                
                dmm = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id,
                    EVMComponent.component_type == "DMM"
                ).first()
                
                if not (cu and cu.status == "counted" and dmm and dmm.status == "counted"):
                    raise HTTPException(status_code=400, detail=f"EVM {pairing.evm_id} not eligible")
            
            # Store data for logging before deletion/modification
            pairing_data_for_logs = []
            component_data_for_logs = []
            flc_data_for_logs = []
            flc_bu_data_for_logs = []
            
            for pairing in pairings:
                # Store pairing data
                pairing_data_for_logs.append({
                    'evm_id': pairing.evm_id,
                    'polling_station_id': pairing.polling_station_id,
                    'created_by_id': pairing.created_by_id,
                    'created_at': pairing.created_at,
                    'completed_by_id': pairing.completed_by_id,
                    'completed_at': pairing.completed_at
                })
                
                # Store component data
                components = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id
                ).all()
                
                for comp in components:
                    component_data_for_logs.append({
                        'serial_number': comp.serial_number,
                        'component_type': comp.component_type,
                        'status': comp.status,
                        'is_verified': comp.is_verified,
                        'dom': comp.dom,
                        'box_no': comp.box_no,
                        'current_user_id': comp.current_user_id,
                        'current_warehouse_id': comp.current_warehouse_id,
                        'pairing_id': comp.pairing_id,
                        'action': 'deleted' if comp.component_type in ["DMM_SEAL", "PINK_PAPER_SEAL"] else 'updated'
                    })
            
            # Store FLC records before deletion
            component_ids = []
            for pairing in pairings:
                components = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id
                ).all()
                component_ids.extend([comp.id for comp in components])
            
            # Get FLC records to log
            flc_records = session.query(FLCRecord).filter(
                or_(
                    FLCRecord.dmm_seal_id.in_(component_ids),
                    FLCRecord.pink_paper_seal_id.in_(component_ids),
                    FLCRecord.dmm_id.in_(component_ids),
                    FLCRecord.cu_id.in_(component_ids)
                )
            ).all()
            
            for flc in flc_records:
                flc_data_for_logs.append({
                    'cu_id': flc.cu_id,
                    'dmm_id': flc.dmm_id,
                    'dmm_seal_id': flc.dmm_seal_id,
                    'pink_paper_seal_id': flc.pink_paper_seal_id,
                    'box_no': flc.box_no,
                    'passed': flc.passed,
                    'remarks': flc.remarks,
                    'flc_by_id': flc.flc_by_id,
                    'flc_date': flc.flc_date
                })
            
            # Get FLCBallotUnit records to log
            flc_bu_records = session.query(FLCBallotUnit).filter(
                FLCBallotUnit.bu_id.in_(component_ids)
            ).all()
            
            for flc_bu in flc_bu_records:
                flc_bu_data_for_logs.append({
                    'bu_id': flc_bu.bu_id,
                    'box_no': flc_bu.box_no,
                    'passed': flc_bu.passed,
                    'remarks': flc_bu.remarks,
                    'flc_by_id': flc_bu.flc_by_id,
                    'flc_date': flc_bu.flc_date
                })
            
            # Delete ALL FLC records that reference ANY of these components
            session.query(FLCRecord).filter(
                or_(
                    FLCRecord.dmm_seal_id.in_(component_ids),
                    FLCRecord.pink_paper_seal_id.in_(component_ids),
                    FLCRecord.dmm_id.in_(component_ids),
                    FLCRecord.cu_id.in_(component_ids)
                )
            ).delete(synchronize_session=False)
            
            # Delete all FLCBallotUnit records
            session.query(FLCBallotUnit).filter(
                FLCBallotUnit.bu_id.in_(component_ids)
            ).delete(synchronize_session=False)
            
            # Now handle components and pairings
            for pairing in pairings:
                components = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id
                ).all()
                
                for comp in components:
                    if comp.component_type in ["DMM_SEAL", "PINK_PAPER_SEAL","BU_PINK_PAPER_SEAL"]:
                        session.delete(comp)
                    elif comp.component_type == "DMM":
                        comp.status = "treasury"
                        comp.pairing_id = None
                        comp.current_user_id = None
                    else:
                        comp.status = "FLC_Pending"
                        comp.pairing_id = None
                
                session.delete(pairing)
            
            session.commit()
            
            # CREATE LOGS - Add corresponding entries to logs tables
            # 1. Log deleted/updated pairing records
            for pairing_data in pairing_data_for_logs:
                pairing_log = PairingRecordLogs(
                    evm_id=pairing_data['evm_id'],
                    polling_station_id=pairing_data['polling_station_id'],
                    created_by_id=pairing_data['created_by_id'],
                    created_at=pairing_data['created_at'],
                    completed_by_id=pairing_data['completed_by_id'],
                    completed_at=pairing_data['completed_at']
                )
                session.add(pairing_log)
                session.commit()
                session.refresh(pairing_log)
                
                # 2. Log component changes (both deleted and updated)
                for comp_data in component_data_for_logs:
                    if comp_data['action'] == 'deleted':
                        # Log deleted components as they were
                        comp_log = EVMComponentLogs(
                            serial_number=comp_data['serial_number'],
                            component_type=comp_data['component_type'],
                            status=comp_data['status'],
                            is_verified=comp_data['is_verified'],
                            dom=comp_data['dom'],
                            box_no=comp_data['box_no'],
                            current_user_id=comp_data['current_user_id'],
                            current_warehouse_id=comp_data['current_warehouse_id'],
                            pairing_id=pairing_log.id
                        )
                    else:
                        # Log updated components with new status
                        new_status = "treasury" if comp_data['component_type'] == "DMM" else "FLC_Pending"
                        comp_log = EVMComponentLogs(
                            serial_number=comp_data['serial_number'],
                            component_type=comp_data['component_type'],
                            status=new_status,
                            is_verified=comp_data['is_verified'],
                            dom=comp_data['dom'],
                            box_no=comp_data['box_no'],
                            current_user_id=comp_data['current_user_id'],
                            current_warehouse_id=comp_data['current_warehouse_id'],
                            pairing_id=None  # Pairing cleared
                        )
                    session.add(comp_log)
            
            # 3. Log deleted FLC records
            for flc_data in flc_data_for_logs:
                # We need to map original component IDs to log IDs
                # For simplicity, we'll log the FLC as is since we can't easily map the IDs
                flc_log = FLCRecordLogs(
                    cu_id=flc_data['cu_id'],  # Note: These reference original component IDs
                    dmm_id=flc_data['dmm_id'],
                    dmm_seal_id=flc_data['dmm_seal_id'],
                    pink_paper_seal_id=flc_data['pink_paper_seal_id'],
                    box_no=flc_data['box_no'],
                    passed=flc_data['passed'],
                    remarks=flc_data['remarks'],
                    flc_by_id=flc_data['flc_by_id'],
                    flc_date=flc_data['flc_date']
                )
                session.add(flc_log)
            
            # 4. Log deleted FLCBallotUnit records
            for flc_bu_data in flc_bu_data_for_logs:
                flc_bu_log = FLCBallotUnitLogs(
                    bu_id=flc_bu_data['bu_id'],  # Note: References original component ID
                    box_no=flc_bu_data['box_no'],
                    passed=flc_bu_data['passed'],
                    remarks=flc_bu_data['remarks'],
                    flc_by_id=flc_bu_data['flc_by_id'],
                    flc_date=flc_bu_data['flc_date']
                )
                session.add(flc_bu_log)
            
            session.commit()
            return Response(status_code=200)
            
        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        
def damaged(evm_id: str):
    """
    Mark a component as damaged
    """
    with Database.get_session() as session:
        evm = session.query(EVMComponent).filter(EVMComponent.serial_number == evm_id).first()
        if not evm:
            raise HTTPException(status_code=404, detail="EVM not found")
        
        if evm.status != "damaged":
            evm.status = "damaged"
            evm.pairing_id = None  
            session.commit()
            return Response(status_code=200)
        else:
            raise HTTPException(status_code=400, detail="EVM already marked as damaged")
        
def view_damaged(district_id: int):
    """
    View all damaged components in a district
    """
    with Database.get_session() as db:
        damaged = db.query(EVMComponent).join(
            User, EVMComponent.current_user_id == User.id
        ).filter(
            EVMComponent.status == "damaged",
            User.district_id == district_id
        ).all()
        if not damaged:
            raise HTTPException(status_code=404, detail="No damaged EVMs found in this district")
        return damaged

def return_to_ecil(component_serial: str):
    """
    Return a component to ECIL
    """
    with Database.get_session() as session:
        component = session.query(EVMComponent).filter(EVMComponent.serial_number == component_serial).first()
        if not component:
            raise HTTPException(status_code=404, detail="EVM not found")
        
        if component.status != "Returned to ECIL":
            component.status = "Returned to ECIL"
            component.current_user_id = 2
            component.is_sec_approved = False
            component.current_warehouse_id = None
            session.commit()
            return Response(status_code=200)
        else:
            raise HTTPException(status_code=400, detail="EVM already marked as returned")
        

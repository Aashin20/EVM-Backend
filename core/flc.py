from core.db import Database
from models.evm import FLCRecord, FLCBallotUnit,FLCDMMUnit, EVMComponentType, EVMComponent, PairingRecord
from models.logs import FLCBallotUnitLogs, FLCRecordLogs, EVMComponentLogs, PairingRecordLogs
from pydantic import BaseModel
from fastapi import HTTPException
from typing import Optional, List
from fastapi.responses import FileResponse
from annexure.Annex_3 import FLC_Certificate_BU, FLC_Certificate_CU
import logging

logger = logging.getLogger(__name__)

class FLCCUModel(BaseModel):
    cu_serial: str
    dmm_serial: str
    dmm_seal_serial: str
    pink_paper_seal_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None

class FLCDMMModel(BaseModel):
    dmm_serial: str
    passed: bool
    remarks: Optional[str] = None

class FLCBUModel(BaseModel):
    bu_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None

def flc_cu(data_list: List[FLCCUModel], user_id: int):
    """Simple optimized FLC CU - All or Nothing approach"""
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            # 1. Get all components in one query
            all_serials = []
            for data in data_list:
                all_serials.extend([data.cu_serial, data.dmm_serial])
            
            components = session.query(EVMComponent).filter(
                EVMComponent.serial_number.in_(all_serials)
            ).all()
            comp_map = {c.serial_number: c for c in components}
            
            # 2. Validate all components exist
            missing = [s for s in all_serials if s not in comp_map]
            if missing:
                raise HTTPException(status_code=404, detail=f"Components not found: {missing}")
            
            # 3. Process each record
            new_components = []
            flc_records = []
            pairings = []
            cu_pdf_data = []
            
            for data in data_list:
                cu = comp_map[data.cu_serial]
                dmm = comp_map[data.dmm_serial]
                
                # Validate component types
                if cu.component_type != EVMComponentType.CU:
                    raise HTTPException(status_code=400, detail=f"Invalid CU: {data.cu_serial}")
                if dmm.component_type != EVMComponentType.DMM:
                    raise HTTPException(status_code=400, detail=f"Invalid DMM: {data.dmm_serial}")
                
                # Create/get seals
                dmm_seal = session.query(EVMComponent).filter_by(
                    serial_number=data.dmm_seal_serial
                ).first()
                if not dmm_seal:
                    dmm_seal = EVMComponent(
                        serial_number=data.dmm_seal_serial,
                        component_type=EVMComponentType.DMM_SEAL,
                        status="FLC_Passed" if data.passed else "FLC_Failed",
                        is_verified=True,
                        box_no=data.box_no,
                        is_sec_approved=True
                    )
                    new_components.append(dmm_seal)
                
                pink_seal = session.query(EVMComponent).filter_by(
                    serial_number=data.pink_paper_seal_serial
                ).first()
                if not pink_seal:
                    pink_seal = EVMComponent(
                        serial_number=data.pink_paper_seal_serial,
                        component_type=EVMComponentType.PINK_PAPER_SEAL,
                        status="FLC_Passed" if data.passed else "FLC_Failed",
                        is_verified=True,
                        box_no=data.box_no,
                        is_sec_approved=True
                    )
                    new_components.append(pink_seal)
                
                # Create pairing
                pairing = PairingRecord(created_by_id=user_id)
                pairings.append(pairing)
                
                # Update component status and box
                status = "FLC_Passed" if data.passed else "FLC_Failed"
                cu.status = status
                cu.box_no = data.box_no
                dmm.status = status
                dmm.box_no = data.box_no
                
                # PDF data
                cu_pdf_data.append({
                    "cu_number": cu.serial_number,
                    "dmm_number": dmm.serial_number,
                    "dmm_seal_no": data.dmm_seal_serial,
                    "cu_pink_seal": data.pink_paper_seal_serial,
                    "passed": data.passed
                })
            
            # 4. Save everything at once
            if new_components:
                session.add_all(new_components)
            session.add_all(pairings)
            session.flush()  # Get IDs for pairings
            
            # 5. Create FLC records and update pairing IDs
            for i, data in enumerate(data_list):
                cu = comp_map[data.cu_serial]
                dmm = comp_map[data.dmm_serial]
                
                # Get seals (either existing or newly created)
                dmm_seal = session.query(EVMComponent).filter_by(
                    serial_number=data.dmm_seal_serial
                ).first()
                pink_seal = session.query(EVMComponent).filter_by(
                    serial_number=data.pink_paper_seal_serial
                ).first()
                
                pairing = pairings[i]
                
                # Update pairing IDs
                cu.pairing_id = pairing.id
                dmm.pairing_id = pairing.id
                dmm_seal.pairing_id = pairing.id
                pink_seal.pairing_id = pairing.id
                
                # Create FLC record
                flc = FLCRecord(
                    cu_id=cu.id,
                    dmm_id=dmm.id,
                    dmm_seal_id=dmm_seal.id,
                    pink_paper_seal_id=pink_seal.id,
                    box_no=data.box_no,
                    passed=data.passed,
                    remarks=data.remarks,
                    flc_by_id=user_id
                )
                flc_records.append(flc)
            
            session.add_all(flc_records)
            session.commit()  # Single commit for all main data
            
            # 6. Create logs (separate transaction for performance)
            _create_cu_logs(session, data_list, user_id)
            
            # 7. Generate PDF
            pdf_filename = FLC_Certificate_CU(cu_pdf_data)
            return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FLC CU error: {e}")
        raise HTTPException(status_code=500, detail="FLC processing failed")

def _create_cu_logs(session, data_list, user_id):
    """Create logs for CU processing"""
    try:
        logs = []
        for data in data_list:
            # Get components
            cu = session.query(EVMComponent).filter_by(serial_number=data.cu_serial).first()
            dmm = session.query(EVMComponent).filter_by(serial_number=data.dmm_serial).first()
            dmm_seal = session.query(EVMComponent).filter_by(serial_number=data.dmm_seal_serial).first()
            pink_seal = session.query(EVMComponent).filter_by(serial_number=data.pink_paper_seal_serial).first()
            
            # Create pairing log
            pairing_log = PairingRecordLogs(
                evm_id=cu.pairing.evm_id if cu.pairing else None,
                polling_station_id=cu.pairing.polling_station_id if cu.pairing else None,
                created_by_id=user_id,
                completed_by_id=cu.pairing.completed_by_id if cu.pairing else None,
                completed_at=cu.pairing.completed_at if cu.pairing else None
            )
            logs.append(pairing_log)
        
        session.add_all(logs)
        session.flush()
        
        # Create component logs
        comp_logs = []
        for i, data in enumerate(data_list):
            pairing_log = logs[i]
            components = [
                session.query(EVMComponent).filter_by(serial_number=data.cu_serial).first(),
                session.query(EVMComponent).filter_by(serial_number=data.dmm_serial).first(),
                session.query(EVMComponent).filter_by(serial_number=data.dmm_seal_serial).first(),
                session.query(EVMComponent).filter_by(serial_number=data.pink_paper_seal_serial).first()
            ]
            
            for comp in components:
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
                comp_logs.append(comp_log)
        
        session.add_all(comp_logs)
        session.flush()
        
        # Create FLC logs
        flc_logs = []
        for i, data in enumerate(data_list):
            start_idx = i * 4
            flc_log = FLCRecordLogs(
                cu_id=comp_logs[start_idx].id,
                dmm_id=comp_logs[start_idx + 1].id,
                dmm_seal_id=comp_logs[start_idx + 2].id,
                pink_paper_seal_id=comp_logs[start_idx + 3].id,
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            flc_logs.append(flc_log)
        
        session.add_all(flc_logs)
        session.commit()
        
    except Exception as e:
        logger.error(f"Error creating CU logs: {e}")
        # Don't fail the main operation for logging errors
        session.rollback()

def flc_bu(data_list: List[FLCBUModel], user_id: int):
    """Simple optimized FLC BU - All or Nothing approach"""
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            # 1. Get all components in one query
            serials = [data.bu_serial for data in data_list]
            components = session.query(EVMComponent).filter(
                EVMComponent.serial_number.in_(serials)
            ).all()
            comp_map = {c.serial_number: c for c in components}
            
            # 2. Validate all components exist
            missing = [s for s in serials if s not in comp_map]
            if missing:
                raise HTTPException(status_code=404, detail=f"Components not found: {missing}")
            
            # 3. Process records
            flc_records = []
            bu_pdf_data = []
            
            for data in data_list:
                bu = comp_map[data.bu_serial]
                
                # Update component
                bu.box_no = data.box_no
                bu.status = "FLC_Passed" if data.passed else "FLC_Failed"
                
                # Create FLC record
                flc = FLCBallotUnit(
                    bu_id=bu.id,
                    box_no=data.box_no,
                    passed=data.passed,
                    remarks=data.remarks,
                    flc_by_id=user_id
                )
                flc_records.append(flc)
                
                # PDF data
                bu_pdf_data.append({
                    "serial_number": bu.serial_number,
                    "passed": data.passed
                })
            
            # 4. Save everything at once
            session.add_all(flc_records)
            session.commit()  # Single commit
            
            # 5. Create logs
            _create_bu_logs(session, data_list, user_id)
            
            # 6. Generate PDF
            pdf_filename = FLC_Certificate_BU(bu_pdf_data)
            return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FLC BU error: {e}")
        raise HTTPException(status_code=500, detail="FLC processing failed")

def _create_bu_logs(session, data_list, user_id):
    """Create logs for BU processing"""
    try:
        comp_logs = []
        for data in data_list:
            bu = session.query(EVMComponent).filter_by(serial_number=data.bu_serial).first()
            
            comp_log = EVMComponentLogs(
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
            comp_logs.append(comp_log)
        
        session.add_all(comp_logs)
        session.flush()
        
        # Create FLC logs
        flc_logs = []
        for i, data in enumerate(data_list):
            flc_log = FLCBallotUnitLogs(
                bu_id=comp_logs[i].id,
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            flc_logs.append(flc_log)
        
        session.add_all(flc_logs)
        session.commit()
        
    except Exception as e:
        logger.error(f"Error creating BU logs: {e}")
        # Don't fail main operation for logging errors
        session.rollback()



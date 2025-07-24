from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo
import tempfile
import os
import logging
import traceback
from fastapi import HTTPException,BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from core.db import Database
from pydantic import BaseModel
from models.evm import (
    EVMComponent, EVMComponentType, PairingRecord, PollingStation
)
from models.users import User
from models.logs import(
    PairingRecordLogs,EVMComponentLogs
)
from annexure.Annex_8 import EVMDetail,RO_PRO
import uuid
from utils.delete_file import remove_file

# Configure logging
logger = logging.getLogger(__name__)

class EVMCommissioningModel(BaseModel):
    evm_no: str
    cu_serial : str
    bu_serial : List[str]
    bu_pink_paper_seals: List[str]  
    ps_no : int

class ReserveEVMCommissioningModel(BaseModel):
    cu_serial: str
    bu_serial: List[str]
    bu_pink_paper_seals: List[str]

def evm_commissioning(commissioning_list: List[EVMCommissioningModel], user_id: int,background_tasks: BackgroundTasks):
    """
    EVM Commissioning fn called by RO
    """
    if not commissioning_list:
        raise HTTPException(status_code=400, detail="No commissioning data provided")
    
    with Database.get_session() as db:
        validation_errors = []
        
        # PHASE 1: COMPLETE VALIDATION (No database changes)
        logger.info(f"Starting validation for {len(commissioning_list)} EVM records")
        
        try:
            for idx, commissioning_data in enumerate(commissioning_list):
                row_num = idx + 1
                
                # Validate polling station number
                try:
                    ps_no = int(commissioning_data.ps_no)
                except (ValueError, TypeError):
                    validation_errors.append(f"Row {row_num}: Invalid polling station number: {commissioning_data.ps_no}")
                    continue
                
                # Validate CU exists and has pairing
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                
                if not cu:
                    validation_errors.append(f"Row {row_num}: CU {commissioning_data.cu_serial} not found")
                    continue
                
                if not cu.pairing_id:
                    validation_errors.append(f"Row {row_num}: CU {commissioning_data.cu_serial} has no pairing record")
                    continue
                
                # Validate pairing record
                pairing = db.query(PairingRecord).filter(
                    PairingRecord.id == cu.pairing_id
                ).first()
                
                if not pairing:
                    validation_errors.append(f"Row {row_num}: Pairing record not found")
                    continue
                
                # Check if already commissioned
                if pairing.polling_station_id:
                    validation_errors.append(f"Row {row_num}: Already assigned to polling station {pairing.polling_station_id}")
                    continue
                
                if pairing.evm_id:
                    validation_errors.append(f"Row {row_num}: Already has EVM number {pairing.evm_id}")
                    continue
                
                # Validate polling station exists
                polling_station = db.query(PollingStation).filter(
                    PollingStation.id == ps_no
                ).first()
                
                if not polling_station:
                    validation_errors.append(f"Row {row_num}: Polling station {ps_no} not found")
                    continue
                
                # Validate all BUs
                if not commissioning_data.bu_serial:
                    validation_errors.append(f"Row {row_num}: No BU serials provided")
                    continue
                
                # Validate BU pink paper seals count matches BU count
                if len(commissioning_data.bu_pink_paper_seals) != len(commissioning_data.bu_serial):
                    validation_errors.append(f"Row {row_num}: BU pink paper seals count ({len(commissioning_data.bu_pink_paper_seals)}) must match BU count ({len(commissioning_data.bu_serial)})")
                    continue
                
                # Check for duplicate BU pink paper seal serials within this commissioning
                if len(set(commissioning_data.bu_pink_paper_seals)) != len(commissioning_data.bu_pink_paper_seals):
                    validation_errors.append(f"Row {row_num}: Duplicate BU pink paper seal serials found")
                    continue
                
                for bu_serial in commissioning_data.bu_serial:
                    bu = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == bu_serial,
                        EVMComponent.component_type == EVMComponentType.BU
                    ).first()
                    
                    if not bu:
                        validation_errors.append(f"Row {row_num}: BU {bu_serial} not found")
                    elif bu.pairing_id and bu.pairing_id != cu.pairing_id:
                        validation_errors.append(f"Row {row_num}: BU {bu_serial} already assigned elsewhere")
                
                # Validate BU pink paper seals (check if they already exist and are available)
                for seal_serial in commissioning_data.bu_pink_paper_seals:
                    existing_seal = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == seal_serial,
                        EVMComponent.component_type == EVMComponentType.BU_PINK_PAPER_SEAL
                    ).first()
                    
                    if existing_seal and existing_seal.pairing_id:
                        validation_errors.append(f"Row {row_num}: BU pink paper seal {seal_serial} already assigned to another pairing")
                
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error during validation: {str(e)}"
            )
        
        # If ANY validation errors, reject entire batch
        if validation_errors:
            logger.warning(f"Validation failed with {len(validation_errors)} errors")
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Validation failed. No EVMs were commissioned.",
                    "errors": validation_errors
                }
            )
        
        # PHASE 2: DATABASE OPERATIONS (All-or-nothing transaction)
        logger.info("Validation passed. Starting database operations")
        
        try:
            current_time = datetime.now(ZoneInfo("Asia/Kolkata"))
            
            # Apply all database changes in single transaction
            for commissioning_data in commissioning_list:
                ps_no = int(commissioning_data.ps_no)
                
                # Get CU and pairing (validated above, so they exist)
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                
                pairing = db.query(PairingRecord).filter(
                    PairingRecord.id == cu.pairing_id
                ).first()
                
                # Update pairing record
                pairing.evm_id = commissioning_data.evm_no
                pairing.polling_station_id = ps_no
                pairing.completed_by_id = user_id
                pairing.completed_at = current_time
                
                # Update CU status
                cu.status = "polling"
                
                # Update all BUs in this pairing and create/assign BU pink paper seals
                for i, bu_serial in enumerate(commissioning_data.bu_serial):
                    bu = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == bu_serial,
                        EVMComponent.component_type == EVMComponentType.BU
                    ).first()
                    bu.pairing_id = cu.pairing_id
                    bu.status = "polling"
                    
                    # Handle BU pink paper seal
                    seal_serial = commissioning_data.bu_pink_paper_seals[i]
                    
                    # Check if BU pink paper seal already exists
                    bu_pink_seal = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == seal_serial,
                        EVMComponent.component_type == EVMComponentType.BU_PINK_PAPER_SEAL
                    ).first()
                    
                    if not bu_pink_seal:
                        # Create new BU pink paper seal inheriting from corresponding BU
                        bu_pink_seal = EVMComponent(
                            serial_number=seal_serial,
                            component_type=EVMComponentType.BU_PINK_PAPER_SEAL,
                            status="polling",  # Same as BU
                            is_allocated=bu.is_allocated,
                            is_verified=bu.is_verified,
                            dom=bu.dom,
                            box_no=bu.box_no,
                            current_user_id=bu.current_user_id,
                            current_warehouse_id=bu.current_warehouse_id,
                            pairing_id=bu.pairing_id,
                            is_sec_approved=True
                        )
                        db.add(bu_pink_seal)
                    else:
                        # Update existing BU pink paper seal
                        bu_pink_seal.pairing_id = bu.pairing_id
                        bu_pink_seal.status = "polling"
                        bu_pink_seal.current_user_id = bu.current_user_id
                        bu_pink_seal.current_warehouse_id = bu.current_warehouse_id
                
                # Update other components (DMM, seals, etc.)
                other_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == cu.pairing_id,
                    EVMComponent.component_type.in_([
                        EVMComponentType.DMM,
                        EVMComponentType.DMM_SEAL,
                        EVMComponentType.PINK_PAPER_SEAL
                    ])
                ).all()
                
                for component in other_components:
                    component.status = "polling"
            
            # Commit all changes
            db.commit()
            logger.info("Database operations completed successfully")
            # PHASE 2.5: MARK REMAINING USER'S COMPONENTS AS RESERVE
            logger.info("Marking remaining user components as reserve")
            
            # Get all components belonging to current user that are not commissioned
            remaining_components = db.query(EVMComponent).filter(
                EVMComponent.current_user_id == user_id,
                EVMComponent.status.in_(["FLC_Pending", "available", "paired"]),
                ~EVMComponent.pairing_id.in_(
                    db.query(PairingRecord.id).filter(
                        PairingRecord.polling_station_id.isnot(None)
                    )
                )
            ).all()
            
            # Update status to reserve for all remaining components
            for component in remaining_components:
                component.status = "reserve"
            
            db.commit()
            logger.info(f"Marked {len(remaining_components)} components as reserve")
            # PHASE 3: CREATE AUDIT LOGS
            logger.info("Creating audit logs")
            
            for commissioning_data in commissioning_list:
                ps_no = int(commissioning_data.ps_no)
                
                # Get updated records
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                
                pairing = db.query(PairingRecord).filter(
                    PairingRecord.id == cu.pairing_id
                ).first()
                
                # Create pairing log
                pairing_log = PairingRecordLogs(
                    evm_id=pairing.evm_id,
                    polling_station_id=pairing.polling_station_id,
                    created_by_id=pairing.created_by_id,
                    created_at=pairing.created_at,
                    completed_by_id=pairing.completed_by_id,
                    completed_at=pairing.completed_at
                )
                db.add(pairing_log)
                db.commit()
                db.refresh(pairing_log)
                
                # Create component logs
                all_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == cu.pairing_id
                ).all()
                
                for component in all_components:
                    comp_log = EVMComponentLogs(
                        serial_number=component.serial_number,
                        component_type=component.component_type,
                        status=component.status,
                        is_verified=component.is_verified,
                        dom=component.dom,
                        box_no=component.box_no,
                        current_user_id=component.current_user_id,
                        current_warehouse_id=component.current_warehouse_id,
                        pairing_id=pairing_log.id
                    )
                    db.add(comp_log)
                
            db.commit()
            logger.info("Audit logs created successfully")
            
            # PHASE 4: GENERATE PDF REPORT
            logger.info("Generating PDF report")
            
            try:
                # Collect data for PDF
                pdf_details = []
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    raise Exception(f"User {user_id} not found")
                
                for commissioning_data in commissioning_list:
                    ps_no = int(commissioning_data.ps_no)
                    
                    # Get commissioned data
                    cu = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == commissioning_data.cu_serial,
                        EVMComponent.component_type == EVMComponentType.CU
                    ).first()
                    
                    pairing = db.query(PairingRecord).filter(
                        PairingRecord.id == cu.pairing_id
                    ).first()
                    
                    polling_station = db.query(PollingStation).filter(
                        PollingStation.id == ps_no
                    ).first()
                    
                    # Get related components
                    bus = db.query(EVMComponent).filter(
                        EVMComponent.pairing_id == cu.pairing_id,
                        EVMComponent.component_type == EVMComponentType.BU
                    ).all()
                    
                    dmm = db.query(EVMComponent).filter(
                        EVMComponent.pairing_id == cu.pairing_id,
                        EVMComponent.component_type == EVMComponentType.DMM
                    ).first()
                    
                    pink_seals = db.query(EVMComponent).filter(
                        EVMComponent.pairing_id == cu.pairing_id,
                        EVMComponent.component_type == EVMComponentType.PINK_PAPER_SEAL
                    ).all()
                    
                    # Get BU pink paper seals
                    bu_pink_seals = db.query(EVMComponent).filter(
                        EVMComponent.pairing_id == cu.pairing_id,
                        EVMComponent.component_type == EVMComponentType.BU_PINK_PAPER_SEAL
                    ).all()
                    
                    # Create EVM detail
                    evm_detail = EVMDetail(
                        evm_no=pairing.evm_id,
                        constituency_ward_no="1",
                        polling_station_no=str(polling_station.id),
                        control_unit_no=cu.serial_number,
                        dmm_no=dmm.serial_number if dmm else "",
                        bu_nos=[bu.serial_number for bu in bus],
                        bu_pink_paper_seal_nos=[seal.serial_number for seal in bu_pink_seals]
                    )
                    
                    pdf_details.append(evm_detail)
                
                # Generate PDF
                temp_dir = tempfile.gettempdir()
                filename = f"EVM_Commissioning_{uuid.uuid4()}.pdf"
                pdf_path = os.path.join(temp_dir, filename)
                
                # Get user details for PDF header
                district_name = user.district.name if user.district else "Unknown District"
                local_body_name = user.local_body.name if user.local_body else "Unknown Local Body"
                ro_name = user.username
                strongroom_name = user.warehouse.name if user.warehouse else "Strongroom 1"
                
                RO_PRO(
                    details=pdf_details,
                    district=district_name,
                    local_body=local_body_name,
                    RO=ro_name,
                    strongroom=strongroom_name,
                    filename=pdf_path
                )
                
                logger.info(f"PDF generated successfully: {filename}")

                background_tasks.add_task(remove_file, filename)

                return FileResponse(
                    path=pdf_path,
                    filename=filename,
                    media_type='application/pdf',
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
                
            except Exception as pdf_error:
                logger.error(f"PDF generation failed: {str(pdf_error)}")
                logger.error(traceback.format_exc())
                
                # Commissioning was successful, but PDF failed
                return {
                    "status": "success",
                    "message": f"Successfully commissioned {len(commissioning_list)} EVMs, but PDF generation failed",
                    "commissioned_count": len(commissioning_list),
                    "pdf_error": str(pdf_error)
                }
            
        except SQLAlchemyError as db_error:
            db.rollback()
            logger.error(f"Database error during commissioning: {str(db_error)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Database error during commissioning: {str(db_error)}"
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during commissioning: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error during commissioning: {str(e)}"
            )

def view_reserve(user_id: int):
    with Database.get_session() as db:
        try:
            reserve_comp = db.query(EVMComponent).filter(
                EVMComponent.current_user_id == user_id,
                EVMComponent.status == "reserve",
                EVMComponent.component_type.in_([
                    EVMComponentType.CU,
                    EVMComponentType.BU,
                    EVMComponentType.DMM,
                ])
            ).all()
            return reserve_comp
        except Exception as e:
            logger.error(f"Error fetching reserve components: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching reserve components: {str(e)}"
            )

def allot_reserve_evm_to_polling_station(
    commissioning_list: List[ReserveEVMCommissioningModel],
    polling_station_id: int,
    user_id: int
):
    with Database.get_session() as db:
        try:
            polling_station = db.query(PollingStation).filter(
                PollingStation.id == polling_station_id
            ).first()
            if not polling_station:
                raise HTTPException(status_code=404, detail="Polling station not found")

            for commissioning_data in commissioning_list:
                # Get reserve CU
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.status == "reserve",
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                if not cu:
                    raise HTTPException(status_code=400, detail=f"Reserve CU {commissioning_data.cu_serial} not found")

                # Pair with BUs
                for i, bu_serial in enumerate(commissioning_data.bu_serial):
                    bu = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == bu_serial,
                        EVMComponent.status == "reserve",
                        EVMComponent.component_type == EVMComponentType.BU
                    ).first()
                    if not bu:
                        raise HTTPException(status_code=400, detail=f"Reserve BU {bu_serial} not found")
                    bu.pairing_id = cu.pairing_id
                    bu.status = "polling"
                    # Assign BU pink paper seal
                    seal_serial = commissioning_data.bu_pink_paper_seals[i]
                    bu_pink_seal = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == seal_serial,
                        EVMComponent.component_type == EVMComponentType.BU_PINK_PAPER_SEAL
                    ).first()
                    if not bu_pink_seal:
                        bu_pink_seal = EVMComponent(
                            serial_number=seal_serial,
                            component_type=EVMComponentType.BU_PINK_PAPER_SEAL,
                            status="polling",
                            pairing_id=cu.pairing_id,
                            is_sec_approved=True
                        )
                        db.add(bu_pink_seal)
                    else:
                        bu_pink_seal.pairing_id = cu.pairing_id
                        bu_pink_seal.status = "polling"

                # Update CU status and pairing
                cu.status = "polling"
                if cu.pairing_id:
                    pairing = db.query(PairingRecord).filter(PairingRecord.id == cu.pairing_id).first()
                    pairing.polling_station_id = polling_station_id
                    pairing.completed_by_id = user_id
                    pairing.completed_at = datetime.now(ZoneInfo("Asia/Kolkata"))

            db.commit()
            return {"status": "success", "message": "Reserve EVM(s) commissioned and allotted to polling station."}
        except Exception as e:
            db.rollback()
            logger.error(f"Error allotting and commissioning reserve EVMs: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error allotting and commissioning reserve EVMs: {str(e)}")
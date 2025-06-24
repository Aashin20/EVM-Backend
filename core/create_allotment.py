from models.evm import (AllotmentItem, Allotment,EVMComponent,
                        AllotmentType, PollingStation,AllotmentItemPending,AllotmentPending)
from models.logs import AllotmentLogs,EVMComponentLogs,AllotmentItemLogs, PairingRecordLogs
from models.users import User,LocalBody,District,Warehouse
from core.db import Database
from pydantic import BaseModel
from typing import Optional,List
from fastapi.exceptions import HTTPException
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import joinedload
from sqlalchemy import and_
from models.evm import PairingRecord, EVMComponentType
from fastapi import Response
import traceback
from fastapi.responses import FileResponse
from annexure.Annex_5 import CUDetail,Deo_BO_CU,BUDetail,Deo_BO_BU
from annexure.Annex_6 import BO_RO_BU, BO_RO_CU

class AllotmentModel(BaseModel):
    allotment_type: AllotmentType
    from_local_body_id: Optional[str] = None #Remove for prod
    from_district_id: Optional[int] = None  #Remove for prod

    to_user_id: int
    evm_component_ids: List[int]
    to_local_body_id: Optional[str] = None
    to_district_id: Optional[int] = None
    original_allotment_id: Optional[int] = None
    reject_reason: Optional[str] = None


def create_allotment(evm: AllotmentModel, from_user_id: int, pending_allotment_id: Optional[int]):  
    print(f"[ALLOTMENT] Starting allotment creation for user {from_user_id}")
    
    with Database.get_session() as db:
        try:
            # Start transaction - everything will be rolled back if any error occurs
            print(f"[ALLOTMENT] Validating {len(evm.evm_component_ids)} components")
            
            components = db.query(EVMComponent).filter(
                EVMComponent.id.in_(evm.evm_component_ids)
            ).all()

            if len(components) != len(evm.evm_component_ids):
                raise HTTPException(status_code=400, detail="Some components not found")

            # If there's a pending allotment, handle components that were removed
            if pending_allotment_id:
                print(f"[ALLOTMENT] Processing pending allotment {pending_allotment_id}")
                # Get all components that were in the pending allotment
                pending_components = db.query(EVMComponent).join(
                    AllotmentItemPending, 
                    EVMComponent.id == AllotmentItemPending.evm_component_id
                ).filter(
                    AllotmentItemPending.allotment_pending_id == pending_allotment_id
                ).all()
                
                # Find components that were removed (in pending but not in final)
                pending_component_ids = {comp.id for comp in pending_components}
                final_component_ids = set(evm.evm_component_ids)
                removed_component_ids = pending_component_ids - final_component_ids
                
                # Reset status for removed components back to "FLC_Passed"
                for comp in pending_components:
                    if comp.id in removed_component_ids:
                        comp.status = "FLC_Passed"

            # Validate component availability and ownership
            for comp in components:
                if comp.status in ["Polled", "Counted","FLC_Failed", "Faulty"]:
                    raise HTTPException(status_code=400, detail=f"Component {comp.serial_number} is not available.")
                if comp.current_user_id != from_user_id:
                    raise HTTPException(status_code=403, detail=f"Component {comp.serial_number} is not owned by the sender.")

            print(f"[ALLOTMENT] Creating allotment record")
            # Create the main allotment
            allotment = Allotment(
                allotment_type=evm.allotment_type,
                from_user_id=from_user_id,
                to_user_id=evm.to_user_id,
                from_local_body_id=evm.from_local_body_id,
                to_local_body_id=evm.to_local_body_id,
                from_district_id=evm.from_district_id,
                to_district_id=evm.to_district_id,
                original_allotment_id=evm.original_allotment_id,
                initiated_by_id=from_user_id,
                status="pending"
            )
            db.add(allotment)
            db.flush()  # Get the ID without committing

            # Create allotment items and update component status
            for comp in components:
                comp.status="FLC_Passed/Temp"
                db.add(AllotmentItem(allotment_id=allotment.id, evm_component_id=comp.id))

            # Delete the pending allotment record if provided
            if pending_allotment_id:
                db.query(AllotmentPending).filter(
                    AllotmentPending.id == pending_allotment_id
                ).delete()

            # Generate PDF if conditions are met
            pdf_filename = None
            
            # DEO to BO/ERO allotments
            if evm.allotment_type == AllotmentType.DEO_TO_BO or evm.allotment_type == AllotmentType.DEO_TO_ERO:
                print(f"[ALLOTMENT] Generating DEO to BO/ERO PDFs")
                pdf_filename = generate_deo_pdfs(db, components, from_user_id, evm)
            
            # BO/ERO to RO allotments  
            elif evm.allotment_type == AllotmentType.BO_TO_RO or evm.allotment_type == AllotmentType.ERO_TO_RO:
                print(f"[ALLOTMENT] Generating BO/ERO to RO PDFs")
                pdf_filename = generate_bo_ero_pdfs(db, components, from_user_id, evm, allotment.id)

            print(f"[ALLOTMENT] Creating audit logs")
            # Create audit logs
            create_allotment_logs(db, allotment, components)

            # Commit everything at once - all or nothing
            db.commit()
            print(f"[ALLOTMENT] Allotment {allotment.id} created successfully")

            # Return FileResponse if PDF was generated, otherwise return JSON
            if pdf_filename:
                print(f"[ALLOTMENT] Returning PDF file: {pdf_filename}")
                return FileResponse(
                    path=pdf_filename,
                    filename=pdf_filename,
                    media_type='application/pdf'
                )
            else:
                return {
                    "id": allotment.id,
                    "allotment_type": allotment.allotment_type,
                    "status": allotment.status,
                    "evm_component_ids": evm.evm_component_ids
                }
                
        except HTTPException:
            # Re-raise HTTP exceptions as they are
            db.rollback()
            print(f"[ALLOTMENT] HTTP Exception occurred, rolling back transaction")
            raise
        except Exception as e:
            # Rollback transaction on any other error
            db.rollback()
            print(f"[ALLOTMENT] Unexpected error occurred: {str(e)}, rolling back transaction")
            print(f"[ALLOTMENT] Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Internal server error during allotment creation")


def generate_deo_pdfs(db, components, from_user_id, evm):
    """Generate PDFs for DEO to BO/ERO allotments"""
    try:
        # Get dynamic alloted_from and alloted_to
        from_user = db.query(User).filter(User.id == from_user_id).first()
        from_district = db.query(District).filter(District.id == from_user.district_id).first() if from_user else None
        
        to_local_body = None
        if evm.to_local_body_id:
            to_local_body = db.query(LocalBody).filter(LocalBody.id == evm.to_local_body_id).first()
        
        alloted_from = from_district.name if from_district else "Unknown"
        alloted_to = to_local_body.name if to_local_body else "Unknown"
        
        pdf_filename = None
        
        # Filter CU components that have paired DMMs
        cu_components = [comp for comp in components if comp.component_type == EVMComponentType.CU and comp.pairing_id is not None]
        
        if cu_components:
            # Get paired DMM components and warehouse details
            cu_details = []
            for cu_comp in cu_components:
                # Get the DMM component from the same pairing
                dmm_comp = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == cu_comp.pairing_id,
                    EVMComponent.component_type == EVMComponentType.DMM
                ).first()
                
                # Get warehouse name
                warehouse_name = "Unknown"
                if cu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == cu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                if dmm_comp:
                    cu_details.append(CUDetail(
                        serial_number=cu_comp.serial_number,
                        box_no=cu_comp.box_no,
                        dmm_no=dmm_comp.serial_number,
                        warehouse=warehouse_name
                    ))
            
            if cu_details:
                # Generate CU PDF
                pdf_filename = Deo_BO_CU(cu_details, alloted_to, alloted_from)
        
        # Filter BU components
        bu_components = [comp for comp in components if comp.component_type == EVMComponentType.BU]
        
        if bu_components:
            # Create BU details
            bu_details = []
            for bu_comp in bu_components:
                # Get warehouse name from current_warehouse_id
                warehouse_name = "Unknown"
                if bu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == bu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                bu_details.append(BUDetail(
                    serial_number=bu_comp.serial_number,
                    box_no=bu_comp.box_no,
                    warehouse=warehouse_name
                ))
            
            if bu_details:
                # Generate BU PDF
                pdf_filename = Deo_BO_BU(bu_details, alloted_to, alloted_from)
        
        return pdf_filename
        
    except Exception as e:
        print(f"[ALLOTMENT] Error generating DEO PDFs: {str(e)}")
        raise


def generate_bo_ero_pdfs(db, components, from_user_id, evm, allotment_id):
    """Generate PDFs for BO/ERO to RO allotments"""
    try:
        # Get dynamic alloted_from and alloted_to
        from_user = db.query(User).filter(User.id == from_user_id).first()
        from_district = db.query(District).filter(District.id == from_user.district_id).first() if from_user else None
        
        to_local_body = None
        if evm.to_local_body_id:
            to_local_body = db.query(LocalBody).filter(LocalBody.id == evm.to_local_body_id).first()
        
        alloted_from = from_district.name if from_district else "Unknown"
        alloted_to = to_local_body.name if to_local_body else "Unknown"
        
        pdf_filename = None
        
        # Filter CU components that have paired DMMs
        cu_components = [comp for comp in components if comp.component_type == EVMComponentType.CU and comp.pairing_id is not None]
        
        if cu_components:
            # Get paired DMM components and warehouse details
            cu_details = []
            for cu_comp in cu_components:
                # Get the DMM component from the same pairing
                dmm_comp = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == cu_comp.pairing_id,
                    EVMComponent.component_type == EVMComponentType.DMM
                ).first()
                
                # Get warehouse name
                warehouse_name = "Unknown"
                if cu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == cu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                if dmm_comp:
                    cu_details.append(CUDetail(
                        serial_number=cu_comp.serial_number,
                        box_no=cu_comp.box_no,
                        dmm_no=dmm_comp.serial_number,
                        warehouse=warehouse_name
                    ))
            
            if cu_details:
                # Generate CU PDF - Convert allotment_id to string
                pdf_filename = BO_RO_CU(cu_details, alloted_to, alloted_from, order_no=str(allotment_id))
        
        # Filter BU components
        bu_components = [comp for comp in components if comp.component_type == EVMComponentType.BU]
        
        if bu_components:
            # Create BU details
            bu_details = []
            for bu_comp in bu_components:
                # Get warehouse name from current_warehouse_id
                warehouse_name = "Unknown"
                if bu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == bu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                bu_details.append(BUDetail(
                    serial_number=bu_comp.serial_number,
                    box_no=bu_comp.box_no,
                    warehouse=warehouse_name
                ))
            
            if bu_details:
                # Generate BU PDF - Convert allotment_id to string
                pdf_filename = BO_RO_BU(bu_details, alloted_to, alloted_from, order_no=str(allotment_id))
        
        return pdf_filename
        
    except Exception as e:
        print(f"[ALLOTMENT] Error generating BO/ERO PDFs: {str(e)}")
        raise


def create_allotment_logs(db, allotment, components):
    """Create audit logs for the allotment"""
    try:
        # Create allotment log
        allotment_log = AllotmentLogs(
            allotment_type=allotment.allotment_type,
            from_user_id=allotment.from_user_id,
            to_user_id=allotment.to_user_id,
            from_local_body_id=allotment.from_local_body_id,
            to_local_body_id=allotment.to_local_body_id,
            from_district_id=allotment.from_district_id,
            to_district_id=allotment.to_district_id,
            status=allotment.status,
            created_at=allotment.created_at
        )
        db.add(allotment_log)
        db.flush()

        # Create component logs
        component_log_ids = []
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
                pairing_id=comp.pairing_id
            )
            db.add(comp_log)
            db.flush()
            component_log_ids.append(comp_log.id)

        # Create allotment item logs
        for i, comp in enumerate(components):
            db.add(AllotmentItemLogs(
                allotment_id=allotment_log.id,
                evm_component_id=component_log_ids[i]
            ))
            
    except Exception as e:
        print(f"[ALLOTMENT] Error creating audit logs: {str(e)}")
        raise
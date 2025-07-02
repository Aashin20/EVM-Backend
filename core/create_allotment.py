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
from annexure.Annex_11 import Return_RO_BO
from annexure.Annex_12 import BO_DEO_Return
from datetime import date

class AllotmentModel(BaseModel):
    allotment_type: AllotmentType
    from_local_body_id: Optional[str] = None
    from_district_id: Optional[int] = None

    to_user_id: Optional[int] = None 
    temporary_allotted_to_name: Optional[str] = None
    temporary_reason: Optional[str] = None
    is_temporary: Optional[bool] = False  

    evm_component_ids: List[int]
    to_local_body_id: Optional[str] = None
    to_district_id: Optional[int] = None
    original_allotment_id: Optional[int] = None
    reject_reason: Optional[str] = None

class CUReturn(BaseModel):
    cu_no: str
    bu_no: str
    dmm_no_return: str
    dmm_no_treasury: str

class ComponentDetail(BaseModel):
    comp_no: str
    comp_type: str  
    comp_box_no: Optional[str] = None
    comp_warehouse: Optional[str] = None


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
                if comp.status in ["Polled", "Counted", "Faulty"]:
                    raise HTTPException(status_code=400, detail=f"Component {comp.serial_number} is not available.")
                if comp.current_user_id != from_user_id:
                    raise HTTPException(status_code=403, detail=f"Component {comp.serial_number} is not owned by the sender.")
            if evm.is_temporary:
                if not evm.temporary_allotted_to_name or not evm.temporary_reason:
                    raise HTTPException(status_code=400, detail="Missing temporary allotment details.")
                if evm.to_user_id:
                    raise HTTPException(status_code=400, detail="Temporary allotments must not include a user ID.")
            else:
                if not evm.to_user_id:
                    raise HTTPException(status_code=400, detail="to_user_id is required for non-temporary allotments.")

            print(f"[ALLOTMENT] Creating allotment record")
            # Create the main allotment
            allotment = Allotment(
                        allotment_type=evm.allotment_type,
                        from_user_id=from_user_id,
                        to_user_id=evm.to_user_id if not evm.is_temporary else None,
                        from_local_body_id=evm.from_local_body_id,
                        to_local_body_id=evm.to_local_body_id,
                        from_district_id=evm.from_district_id,
                        to_district_id=evm.to_district_id,
                        original_allotment_id=evm.original_allotment_id,
                        initiated_by_id=from_user_id,
                        status="pending",
                        is_temporary=evm.is_temporary,
                        temporary_allotted_to_name=evm.temporary_allotted_to_name if evm.is_temporary else None,
                        temporary_reason=evm.temporary_reason if evm.is_temporary else None
                    )

            db.add(allotment)
            db.flush()  # Get the ID without committing

            # Create allotment items and update component status
            for comp in components:
                comp.status="FLC_Passed/Temp"
                comp.last_received_from_id = from_user_id
                comp.date_of_receipt = date.today()
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
            
            # RO to BO/ERO returns
            elif evm.allotment_type == AllotmentType.RO_TO_BO or evm.allotment_type == AllotmentType.RO_TO_ERO:
                print(f"[ALLOTMENT] Generating RO to BO/ERO return PDF")
                pdf_filename = generate_bo_ro_return_pdf(db, components, from_user_id, evm)
            
            # BO/ERO to DEO returns
            elif evm.allotment_type == AllotmentType.BO_TO_DEO or evm.allotment_type == AllotmentType.ERO_TO_DEO:
                print(f"[ALLOTMENT] Generating BO/ERO to DEO return PDF")
                pdf_filename = generate_bo_ero_deo_pdf(db, components, from_user_id, evm, allotment.id)

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

def generate_bo_ro_return_pdf(db, components, from_user_id, evm):
    """Generate PDF for RO to BO/ERO returns (Annexure 11) - Production Ready"""
    try:
        print(f"[ALLOTMENT] Starting RO return PDF generation for {len(components)} components")
        
        # Validate inputs
        if not components:
            print(f"[ALLOTMENT] No components provided for RO return PDF")
            return None
            
        # Get from_user with error handling
        from_user = db.query(User).filter(User.id == from_user_id).first()
        if not from_user:
            print(f"[ALLOTMENT] From user {from_user_id} not found")
            raise HTTPException(status_code=400, detail=f"User {from_user_id} not found")
            
        ro_name = from_user.username or "Unknown"
        
        # Get alloted_to with comprehensive error handling
        alloted_to = "Unknown"
        try:
            if evm.to_local_body_id:
                to_local_body = db.query(LocalBody).filter(LocalBody.id == evm.to_local_body_id).first()
                if to_local_body:
                    alloted_to = to_local_body.name
                else:
                    print(f"[ALLOTMENT] Warning: Local body {evm.to_local_body_id} not found")
            elif evm.to_district_id:
                to_district = db.query(District).filter(District.id == evm.to_district_id).first()
                if to_district:
                    alloted_to = to_district.name
                else:
                    print(f"[ALLOTMENT] Warning: District {evm.to_district_id} not found")
        except Exception as e:
            print(f"[ALLOTMENT] Error getting destination details: {str(e)}")
            # Continue with "Unknown" - don't fail the entire process
        
        # Safely filter components with validation
        try:
            cu_components = [comp for comp in components if comp.component_type == EVMComponentType.CU]
            bu_components = [comp for comp in components if comp.component_type == EVMComponentType.BU]
            dmm_return_components = [comp for comp in components 
                                   if comp.component_type == EVMComponentType.DMM and comp.status != "treasury"]
            dmm_treasury_components = [comp for comp in components 
                                     if comp.component_type == EVMComponentType.DMM and comp.status == "treasury"]
        except AttributeError as e:
            print(f"[ALLOTMENT] Error filtering components: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid component data structure")
        
        # Log component counts for debugging
        print(f"[ALLOTMENT] Found - CUs: {len(cu_components)}, BUs: {len(bu_components)}, "
              f"DMM Returns: {len(dmm_return_components)}, DMM Treasury: {len(dmm_treasury_components)}")
        
        # Validate that we have CU components (minimum requirement)
        if not cu_components:
            print(f"[ALLOTMENT] No CU components found for RO return PDF")
            return None
        
        # Create CUReturn details with safe pairing
        cu_return_details = []
        max_components = len(cu_components)
        
        for i in range(max_components):
            try:
                cu_comp = cu_components[i]
                
                # Safely get other components with bounds checking
                bu_no = bu_components[i].serial_number if i < len(bu_components) else ""
                dmm_no_return = dmm_return_components[i].serial_number if i < len(dmm_return_components) else ""
                dmm_no_treasury = dmm_treasury_components[i].serial_number if i < len(dmm_treasury_components) else ""
                
                # Validate CU component has required data
                if not cu_comp.serial_number:
                    print(f"[ALLOTMENT] Warning: CU component at index {i} has no serial number")
                    continue
                
                cu_return_details.append(CUReturn(
                    cu_no=cu_comp.serial_number,
                    bu_no=bu_no,
                    dmm_no_return=dmm_no_return,
                    dmm_no_treasury=dmm_no_treasury
                ))
                
            except Exception as e:
                print(f"[ALLOTMENT] Error processing component at index {i}: {str(e)}")
                # Continue processing other components instead of failing entirely
                continue
        
        # Final validation before PDF generation
        if not cu_return_details:
            print(f"[ALLOTMENT] No valid CU return details created")
            return None
            
        print(f"[ALLOTMENT] Generated {len(cu_return_details)} CU return details")
        
        # Generate PDF with error handling
        try:
            pdf_filename = Return_RO_BO(
                details=cu_return_details,
                RO=ro_name,
                alloted_to=alloted_to
            )
            
            if pdf_filename:
                print(f"[ALLOTMENT] Successfully generated RO return PDF: {pdf_filename}")
                return pdf_filename
            else:
                print(f"[ALLOTMENT] PDF generation returned None")
                return None
                
        except Exception as e:
            print(f"[ALLOTMENT] Error in Return_RO_BO PDF generation: {str(e)}")
            # Log the error but don't fail the entire allotment process
            print(f"[ALLOTMENT] CU return details that failed: {len(cu_return_details)} items")
            raise HTTPException(status_code=500, detail="PDF generation failed")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"[ALLOTMENT] Unexpected error in RO return PDF generation: {str(e)}")
        print(f"[ALLOTMENT] Traceback: {traceback.format_exc()}")
        # Don't fail the entire allotment - just skip PDF generation
        return None

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
                warehouse_name = "Warehouse 1"
                if cu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == cu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                if dmm_comp:
                    cu_details.append(CUDetail(
                        serial_number=cu_comp.serial_number,
                        box_no=str(cu_comp.box_no) if cu_comp.box_no is not None else "",
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
                warehouse_name = "Warehouse 1"
                if bu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == bu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                bu_details.append(BUDetail(
                    serial_number=bu_comp.serial_number,
                    box_no=str(bu_comp.box_no) if bu_comp.box_no is not None else "",
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
                warehouse_name = "Warehouse 1"
                if cu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == cu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                if dmm_comp:
                    cu_details.append(CUDetail(
                        serial_number=cu_comp.serial_number,
                        box_no=str(cu_comp.box_no) if cu_comp.box_no is not None else "",
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
                warehouse_name = "Warehouse 1"
                if bu_comp.current_warehouse_id:
                    warehouse = db.query(Warehouse).filter(Warehouse.id == bu_comp.current_warehouse_id).first()
                    if warehouse:
                        warehouse_name = warehouse.name
                
                bu_details.append(BUDetail(
                    serial_number=bu_comp.serial_number,
                    box_no=str(bu_comp.box_no) if bu_comp.box_no is not None else "",
                    warehouse=warehouse_name
                ))
            
            if bu_details:
                # Generate BU PDF - Convert allotment_id to string
                pdf_filename = BO_RO_BU(bu_details, alloted_to, alloted_from, order_no=str(allotment_id))
        
        return pdf_filename
        
    except Exception as e:
        print(f"[ALLOTMENT] Error generating BO/ERO PDFs: {str(e)}")
        raise


def generate_bo_ero_deo_pdf(db, components, from_user_id, evm, allotment_id):
    """Generate PDF for BO/ERO to DEO returns (Annexure 12)"""
    try:
        # Get alloted_from (from_user's local body or district)
        from_user = db.query(User).filter(User.id == from_user_id).first()
        alloted_from = "Unknown"
        
        if from_user:
            if evm.from_local_body_id:
                from_local_body = db.query(LocalBody).filter(LocalBody.id == evm.from_local_body_id).first()
                alloted_from = from_local_body.name if from_local_body else "Unknown"
            elif from_user.district_id:
                from_district = db.query(District).filter(District.id == from_user.district_id).first()
                alloted_from = from_district.name if from_district else "Unknown"
        
        # Get alloted_to (DEO district)
        to_district = None
        if evm.to_district_id:
            to_district = db.query(District).filter(District.id == evm.to_district_id).first()
        
        alloted_to = to_district.name if to_district else "Unknown"
        
        # Prepare component details
        component_details = []
        
        for comp in components:
            # Get warehouse name
            warehouse_name = "Warehouse 1"
            if comp.current_warehouse_id:
                warehouse = db.query(Warehouse).filter(Warehouse.id == comp.current_warehouse_id).first()
                if warehouse:
                    warehouse_name = warehouse.name
            
            component_details.append(ComponentDetail(
                comp_no=comp.serial_number,
                comp_type=comp.component_type.value,
                comp_box_no=str(comp.box_no) if comp.box_no is not None else None,
                comp_warehouse=warehouse_name
            ))
        
        # Generate PDF if we have component details
        if component_details:
            pdf_filename = BO_DEO_Return(
                details=component_details,
                order_no=str(allotment_id),
                alloted_from=alloted_from,
                alloted_to=alloted_to
            )
            return pdf_filename
        
        return None
        
    except Exception as e:
        print(f"[ALLOTMENT] Error generating BO/ERO return PDF: {str(e)}")
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
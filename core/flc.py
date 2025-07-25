from core.db import Database
from models.evm import FLCRecord, FLCBallotUnit, FLCDMMUnit, EVMComponentType, EVMComponent, PairingRecord,BoxNumber
from models.logs import FLCBallotUnitLogs, FLCRecordLogs, EVMComponentLogs, PairingRecordLogs
from pydantic import BaseModel
from fastapi import HTTPException,BackgroundTasks,Response
from typing import Optional, List,Any
from fastapi.responses import FileResponse
from annexure.Annex_3 import FLC_Certificate_BU, FLC_Certificate_CU
from annexure.box_wise_sticker import Box_wise_sticker
import logging
from models.users import User
from sqlalchemy import and_
from datetime import datetime
from utils.delete_file import remove_file
from models.users import District

logger = logging.getLogger(__name__)

class FLCCUModel(BaseModel):
    cu_serial: str
    cu_dom: str
    dmm_serial: str
    dmm_dom: str
    dmm_seal_serial: str
    pink_paper_seal_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None

class FLCDMMModel(BaseModel):
    dmm_serial: str
    dmm_dom: Optional[str] = None
    passed: bool
    remarks: Optional[str] = None

class FLCBUModel(BaseModel):
    bu_serial: str
    bu_dom: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None

def get_deo_user_id(session, user_id: int) -> int:
    user = session.query(User).filter(User.id == user_id).first()
    if not user or not user.district_id:
        raise HTTPException(status_code=400, detail="User district not found")
    
    deo = session.query(User).filter(
        User.role_id == 2,
        User.district_id == user.district_id
    ).first()
    
    if not deo:
        raise HTTPException(status_code=400, detail="DEO not found")
    
    return deo.id

def create_or_update_component(session, serial: str, component_type: EVMComponentType, 
                             dom: Optional[str], box_no: str, deo_user_id: int, passed: bool) -> tuple[EVMComponent, EVMComponentLogs]:
    component = session.query(EVMComponent).filter_by(serial_number=serial).first()
    status = "FLC_Passed" if passed else "FLC_Failed"
    
    if component:
        component.status = status
        component.box_no = box_no
    else:
        component = EVMComponent(
            serial_number=serial,
            component_type=component_type,
            dom=dom,
            box_no=box_no,
            current_user_id=deo_user_id,
            last_received_from_id=3,
            date_of_receipt=datetime.now(),
            status=status,
            is_verified=True,
            is_sec_approved=True
        )
        session.add(component)
        session.flush()
        
    # Create component log entry
    component_log = EVMComponentLogs(
        serial_number=component.serial_number,
        component_type=component.component_type,
        status=component.status,
        is_verified=component.is_verified,
        dom=component.dom,
        box_no=component.box_no,
        current_user_id=component.current_user_id,
        current_warehouse_id=component.current_warehouse_id,
        pairing_id=component.pairing_id
    )
    session.add(component_log)
    session.flush()
    return component, component_log

from sqlalchemy import func
from typing import Dict, Set

def validate_and_prepare_boxes(session, box_assignments: Dict[str, int]) -> None:
    
    # Get all unique box numbers
    box_numbers = list(box_assignments.keys())
    
    # Query existing boxes
    existing_boxes = session.query(BoxNumber).filter(
        BoxNumber.box_no.in_(box_numbers)
    ).all()
    
    existing_box_dict = {box.box_no: box for box in existing_boxes}
    
    # Validate capacity and prepare new boxes
    new_boxes = []
    
    for box_no, components_to_add in box_assignments.items():
        if box_no in existing_box_dict:
            # Check if adding components would exceed limit
            current_count = existing_box_dict[box_no].num_components
            if current_count + components_to_add > 10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Box {box_no} would exceed capacity. Current: {current_count}, "
                           f"Trying to add: {components_to_add}, Max: 10"
                )
        else:
            # New box - check if components would exceed limit
            if components_to_add > 10:
                raise HTTPException(
                    status_code=400,
                    detail=f"Box {box_no} would exceed capacity with {components_to_add} components"
                )
            # Create new box record
            new_box = BoxNumber(box_no=box_no, num_components=0)
            new_boxes.append(new_box)
            existing_box_dict[box_no] = new_box
    
    # Add all new boxes to session
    if new_boxes:
        session.add_all(new_boxes)
        session.flush()


def validate_component_box_assignment(session, component_serials: Set[str], 
                                    component_box_map: Dict[str, str]) -> None:
   
    # Query existing components
    existing_components = session.query(
        EVMComponent.serial_number,
        EVMComponent.box_no
    ).filter(
        EVMComponent.serial_number.in_(component_serials),
        EVMComponent.box_no.isnot(None)
    ).all()
    
    # Check for conflicts
    for comp in existing_components:
        new_box = component_box_map.get(comp.serial_number)
        if new_box and comp.box_no != new_box:
            raise HTTPException(
                status_code=400,
                detail=f"Component {comp.serial_number} already exists in box {comp.box_no}, "
                       f"cannot move to box {new_box}"
            )


def update_box_counts(session, box_assignments: Dict[str, int]) -> None:
  
    for box_no, count in box_assignments.items():
        session.query(BoxNumber).filter(
            BoxNumber.box_no == box_no
        ).update({
            BoxNumber.num_components: BoxNumber.num_components + count
        })

def flc_cu(data_list: List[FLCCUModel], user_id: int, background_tasks: BackgroundTasks):
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            # Pre-validation: Count components per box and check assignments
            box_assignments = {}  # box_no -> component count
            component_box_map = {}  # serial_number -> box_no
            all_cu_serials = set()
            
            for data in data_list:
                # Only CU components count towards box limit
                box_assignments[data.box_no] = box_assignments.get(data.box_no, 0) + 1
                component_box_map[data.cu_serial] = data.box_no
                all_cu_serials.add(data.cu_serial)
            
            # Validate box capacity
            validate_and_prepare_boxes(session, box_assignments)
            
            # Validate component box assignments
            validate_component_box_assignment(session, all_cu_serials, component_box_map)
            
            # Process FLC records
            deo_user_id = get_deo_user_id(session, user_id)
            flc_records = []
            pairings = []
            
            for data in data_list:
                cu, cu_log = create_or_update_component(
                    session, data.cu_serial, EVMComponentType.CU, 
                    data.cu_dom, data.box_no, deo_user_id, data.passed
                )
                dmm, dmm_log = create_or_update_component(
                    session, data.dmm_serial, EVMComponentType.DMM, 
                    data.dmm_dom, data.box_no, deo_user_id, data.passed
                )
                dmm_seal, dmm_seal_log = create_or_update_component(
                    session, data.dmm_seal_serial, EVMComponentType.DMM_SEAL, 
                    None, data.box_no, deo_user_id, data.passed  # Pass None for dom
                )
                pink_seal, pink_seal_log = create_or_update_component(
                    session, data.pink_paper_seal_serial, EVMComponentType.PINK_PAPER_SEAL, 
                    None, data.box_no, deo_user_id, data.passed  # Pass None for dom
                )
                
                # Ensure all component logs are flushed before creating pairing
                session.flush()
                
                pairing = PairingRecord(created_by_id=user_id)
                session.add(pairing)
                session.flush()
                
                cu.pairing_id = pairing.id
                dmm.pairing_id = pairing.id
                dmm_seal.pairing_id = pairing.id
                pink_seal.pairing_id = pairing.id
                
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
                
                # Store log IDs for later use in FLC logs
                flc.cu_log_id = cu_log.id
                flc.dmm_log_id = dmm_log.id
                flc.dmm_seal_log_id = dmm_seal_log.id
                flc.pink_paper_seal_log_id = pink_seal_log.id
            
            session.add_all(flc_records)
            session.flush()  # Flush FLC records before creating logs
            
            create_cu_flc_logs(session, flc_records, user_id)
            
            # Update box counts after successful processing
            update_box_counts(session, box_assignments)
            
            session.commit()
            
            return Response(status_code=200, content="FLC processing completed successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FLC CU error: {e}")
        raise HTTPException(status_code=500, detail="FLC processing failed")


def flc_bu(data_list: List[FLCBUModel], user_id: int, background_tasks: BackgroundTasks):
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            # Pre-validation: Count components per box and check assignments
            box_assignments = {}  # box_no -> component count
            component_box_map = {}  # serial_number -> box_no
            all_bu_serials = set()
            
            for data in data_list:
                # BU components count towards box limit
                box_assignments[data.box_no] = box_assignments.get(data.box_no, 0) + 1
                component_box_map[data.bu_serial] = data.box_no
                all_bu_serials.add(data.bu_serial)
            
            # Validate box capacity
            validate_and_prepare_boxes(session, box_assignments)
            
            # Validate component box assignments
            validate_component_box_assignment(session, all_bu_serials, component_box_map)
            
            # Process FLC records
            deo_user_id = get_deo_user_id(session, user_id)
            flc_records = []
            
            for data in data_list:
                bu, bu_log = create_or_update_component(
                    session, data.bu_serial, EVMComponentType.BU, 
                    data.bu_dom, data.box_no, deo_user_id, data.passed
                )
                
                flc = FLCBallotUnit(
                    bu_id=bu.id,
                    box_no=data.box_no,
                    passed=data.passed,
                    remarks=data.remarks,
                    flc_by_id=user_id
                )
                # Store log ID for later use in FLC logs
                flc.bu_log_id = bu_log.id
                flc_records.append(flc)
            
            session.add_all(flc_records)
            session.flush()  # Flush FLC records before creating logs
            
            create_bu_flc_logs(session, flc_records, user_id)
            
            # Update box counts after successful processing
            update_box_counts(session, box_assignments)
            
            session.commit()
            
            return Response(status_code=200, content="FLC processing completed successfully")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FLC BU error: {e}")
        raise HTTPException(status_code=500, detail="FLC processing failed")

def create_cu_flc_logs(session, flc_records, user_id):
    # Create pairing logs first
    pairing_logs = []
    for flc_record in flc_records:
        cu = session.query(EVMComponent).filter_by(id=flc_record.cu_id).first()
        pairing_log = PairingRecordLogs(
            evm_id=cu.pairing.evm_id if cu.pairing else None,
            polling_station_id=cu.pairing.polling_station_id if cu.pairing else None,
            created_by_id=user_id,
            completed_by_id=cu.pairing.completed_by_id if cu.pairing else None,
            completed_at=cu.pairing.completed_at if cu.pairing else None
        )
        pairing_logs.append(pairing_log)
    
    session.add_all(pairing_logs)
    session.flush()
    
    # Create FLC logs using the component log IDs
    flc_logs = []
    for flc_record in flc_records:
        flc_log = FLCRecordLogs(
            cu_id=getattr(flc_record, 'cu_log_id', flc_record.cu_id),
            dmm_id=getattr(flc_record, 'dmm_log_id', flc_record.dmm_id),
            dmm_seal_id=getattr(flc_record, 'dmm_seal_log_id', flc_record.dmm_seal_id),
            pink_paper_seal_id=getattr(flc_record, 'pink_paper_seal_log_id', flc_record.pink_paper_seal_id),
            box_no=flc_record.box_no,
            passed=flc_record.passed,
            remarks=flc_record.remarks,
            flc_by_id=user_id
        )
        flc_logs.append(flc_log)
    
    session.add_all(flc_logs)

def create_bu_flc_logs(session, flc_records, user_id):
    flc_logs = []
    for flc_record in flc_records:
        flc_log = FLCBallotUnitLogs(
            bu_id=getattr(flc_record, 'bu_log_id', flc_record.bu_id),
            box_no=flc_record.box_no,
            passed=flc_record.passed,
            remarks=flc_record.remarks,
            flc_by_id=user_id
        )
        flc_logs.append(flc_log)
    
    session.add_all(flc_logs)

def flc_dmm(data_list: List[FLCDMMModel], user_id: int, background_tasks: BackgroundTasks):
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            dmm_serials = [data.dmm_serial for data in data_list]
            
            if len(dmm_serials) != len(set(dmm_serials)):
                raise HTTPException(status_code=400, detail="Duplicate DMM serials in request")
            
            existing_components = session.query(EVMComponent.serial_number).filter(
                EVMComponent.serial_number.in_(dmm_serials)
            ).all()
            
            if existing_components:
                existing_serials = [comp.serial_number for comp in existing_components]
                raise HTTPException(
                    status_code=409, 
                    detail=f"DMM components already exist: {', '.join(existing_serials)}"
                )
            
            deo_user_id = get_deo_user_id(session, user_id)
            flc_records = []
            
            for data in data_list:
                dmm, dmm_log = create_or_update_component(
                    session, data.dmm_serial, EVMComponentType.DMM, 
                    data.dmm_dom, None, deo_user_id, data.passed
                )
                
                flc = FLCDMMUnit(
                    dmm_id=dmm.id,
                    passed=data.passed,
                    remarks=data.remarks,
                    flc_by_id=user_id
                )
                flc.dmm_log_id = dmm_log.id
                flc_records.append(flc)
            
            session.add_all(flc_records)
            session.flush()
            
            create_dmm_flc_logs(session, flc_records, user_id)
            session.commit()
            
            return Response(status_code=200, content="FLC DMM processing completed successfully")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FLC DMM error: {e}")
        raise HTTPException(status_code=500, detail="DMM FLC processing failed")
    
def create_dmm_flc_logs(session, flc_records, user_id):
    flc_logs = []
    for flc_record in flc_records:
        flc_log = FLCRecordLogs(
            cu_id=None,
            dmm_id=getattr(flc_record, 'dmm_log_id', flc_record.dmm_id),
            dmm_seal_id=None,
            pink_paper_seal_id=None,
            box_no=None,
            passed=flc_record.passed,
            remarks=flc_record.remarks,
            flc_by_id=user_id
        )
        flc_logs.append(flc_log)
    
    session.add_all(flc_logs)

def generate_box_wise_sticker(district_id: str, filename: str = "Box_Wise_Sticker.pdf") -> str:
    try:
        with Database.get_session() as db:
            components = db.query(
                EVMComponent.box_no,
                EVMComponent.serial_number,
                EVMComponent.status,
                EVMComponent.id,
                EVMComponent.component_type
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).filter(
                User.district_id == district_id,
                EVMComponent.component_type.in_([
                    EVMComponentType.CU,
                    EVMComponentType.BU
                ])
            ).order_by(
                EVMComponent.box_no.nulls_last(),
                EVMComponent.serial_number
            ).all()
            
            component_ids = [comp.id for comp in components]
            
            flc_cu_dates = {}
            if component_ids:
                flc_cu_query = db.query(
                    FLCRecord.cu_id,
                    FLCRecord.flc_date
                ).filter(
                    FLCRecord.cu_id.in_(component_ids)
                ).all()
                
                flc_cu_dates = {record.cu_id: record.flc_date for record in flc_cu_query}
            
            flc_bu_dates = {}
            if component_ids:
                flc_bu_query = db.query(
                    FLCBallotUnit.bu_id,
                    FLCBallotUnit.flc_date
                ).filter(
                    FLCBallotUnit.bu_id.in_(component_ids)
                ).all()
                
                flc_bu_dates = {record.bu_id: record.flc_date for record in flc_bu_query}
            
            box_dict = {}
            for component in components:
                box_no = component.box_no if component.box_no is not None else "Unboxed"
                
                if box_no not in box_dict:
                    box_dict[box_no] = []
                
                flc_date = None
                if component.component_type == EVMComponentType.CU:
                    flc_date = flc_cu_dates.get(component.id)
                elif component.component_type == EVMComponentType.BU:
                    flc_date = flc_bu_dates.get(component.id)
                
                box_dict[box_no].append({
                    "serial_no": component.serial_number,
                    "status": component.status,
                    "flc_date": flc_date.isoformat() if flc_date else None
                })
            
            sorted_boxes = sorted(
                box_dict.keys(),
                key=lambda x: (x == "Unboxed", x if x != "Unboxed" else float('inf'))
            )
            
            boxes_data = []
            for box_no in sorted_boxes:
                boxes_data.append({
                    "box_no": box_no,
                    "components": box_dict[box_no]
                })
            
            pdf = Box_wise_sticker(boxes_data, filename)
            return FileResponse(pdf, media_type='application/pdf', filename="Box_Wise_Sticker.pdf")
            
    except Exception as e:
        logger.error(f"Error generating box wise sticker: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")
    
def generate_dmm_flc_pdf(district_id: int, background_tasks: BackgroundTasks):
    try:
        with Database.get_session() as session:
            flc_records = session.query(FLCDMMUnit).join(
                User, FLCDMMUnit.flc_by_id == User.id
            ).filter(
                User.district_id == district_id
            ).all()
            
            if not flc_records:
                raise HTTPException(status_code=404, detail="No DMM FLC records found for this district")
            
            pdf_data = []
            for flc in flc_records:
                dmm = session.query(EVMComponent).filter(EVMComponent.id == flc.dmm_id).first()
                
                pdf_data.append({
                    "cu_number": "",
                    "dmm_number": dmm.serial_number if dmm else "",
                    "dmm_seal_no": "",
                    "cu_pink_seal": "",
                    "passed": flc.passed
                })
            
            pdf_filename = FLC_Certificate_CU(pdf_data)
            background_tasks.add_task(remove_file, pdf_filename)
            return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DMM PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")
    

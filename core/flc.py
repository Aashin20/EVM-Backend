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
from sqlalchemy import func
from typing import Dict, Set
from core.db import Database
from models.evm import FLCRecord, FLCBallotUnit, FLCDMMUnit, EVMComponentType, EVMComponent, PairingRecord, BoxNumber
from models.logs import FLCBallotUnitLogs, FLCRecordLogs, EVMComponentLogs, PairingRecordLogs
from pydantic import BaseModel
from fastapi import HTTPException, BackgroundTasks, Response
from typing import Optional, List, Any, Dict, Set
from fastapi.responses import FileResponse
from annexure.Annex_3 import FLC_Certificate_BU, FLC_Certificate_CU
from annexure.box_wise_sticker import Box_wise_sticker
import logging
from models.users import User, District
from sqlalchemy import and_, func
from datetime import datetime
from utils.delete_file import remove_file
from sqlalchemy.orm import aliased
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class FLCCUModel(BaseModel):
    cu_serial: str
    cu_dom: str
    dmm_serial: Optional[str] = None
    dmm_dom: Optional[str] = None
    dmm_seal_serial: Optional[str] = None
    pink_paper_seal_serial: Optional[str] = None
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
        
    component_log = EVMComponentLogs(
        serial_number=component.serial_number,
        component_type=component.component_type,
        status=component.status,
        is_verified=component.is_verified,
        dom=component.dom,
        box_no=component.box_no,
        current_user_id=component.current_user_id,
        current_warehouse_id=component.current_warehouse_id,
        pairing_id=None
    )
    session.add(component_log)
    session.flush()
    return component, component_log

def create_or_update_component_safe(session, serial: str, component_type: EVMComponentType, 
                                  dom: Optional[str], box_no: str, deo_user_id: int, 
                                  passed: bool, pairing_id: Optional[int] = None) -> tuple[EVMComponent, EVMComponentLogs]:
    component = session.query(EVMComponent).filter_by(serial_number=serial).first()
    status = "FLC_Passed" if passed else "FLC_Failed"
    
    if component:
        component.status = status
        component.box_no = box_no
        if pairing_id:
            component.pairing_id = pairing_id
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
            is_sec_approved=True,
            pairing_id=pairing_id
        )
        session.add(component)
        session.flush()
        
    component_log = EVMComponentLogs(
        serial_number=component.serial_number,
        component_type=component.component_type,
        status=component.status,
        is_verified=component.is_verified,
        dom=component.dom,
        box_no=component.box_no,
        current_user_id=component.current_user_id,
        current_warehouse_id=component.current_warehouse_id,
        pairing_id=pairing_id if pairing_id else None
    )
    session.add(component_log)
    session.flush()
    return component, component_log

def validate_and_prepare_boxes(session, box_assignments: Dict[str, int]) -> None:
    box_numbers = list(box_assignments.keys())
    existing_boxes = session.query(BoxNumber).filter(BoxNumber.box_no.in_(box_numbers)).all()
    existing_box_dict = {box.box_no: box for box in existing_boxes}
    new_boxes = []
    
    for box_no, components_to_add in box_assignments.items():
        if box_no in existing_box_dict:
            current_count = existing_box_dict[box_no].num_components
            if current_count + components_to_add > 10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Box {box_no} would exceed capacity. Current: {current_count}, "
                           f"Trying to add: {components_to_add}, Max: 10"
                )
        else:
            if components_to_add > 10:
                raise HTTPException(
                    status_code=400,
                    detail=f"Box {box_no} would exceed capacity with {components_to_add} components"
                )
            new_box = BoxNumber(box_no=box_no, num_components=0)
            new_boxes.append(new_box)
            existing_box_dict[box_no] = new_box
    
    if new_boxes:
        session.add_all(new_boxes)
        session.flush()

def validate_component_box_assignment(session, component_serials: Set[str], 
                                    component_box_map: Dict[str, str]) -> None:
    existing_components = session.query(
        EVMComponent.serial_number,
        EVMComponent.box_no
    ).filter(
        EVMComponent.serial_number.in_(component_serials),
        EVMComponent.box_no.isnot(None)
    ).all()
    
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

def create_cu_flc_logs_simple(session, flc_records, user_id):
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

def flc_cu(data_list: List[FLCCUModel], user_id: int, background_tasks: BackgroundTasks):
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            # Collect all serials for duplicate validation
            all_serials = set()
            seen_serials = set()
            batch_duplicates = set()
            
            for data in data_list:
                # Validate input consistency for complete records
                has_dmm = bool(data.dmm_serial)
                has_dmm_seal = bool(data.dmm_seal_serial) 
                has_pink_seal = bool(data.pink_paper_seal_serial)
                
                optional_fields = [has_dmm, has_dmm_seal, has_pink_seal]
                if any(optional_fields) and not all(optional_fields):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Incomplete component set for CU {data.cu_serial}. "
                               f"Either provide all components (dmm, dmm_seal, pink_paper_seal) or only CU."
                    )
                
                # Collect serials and check for batch duplicates
                record_serials = [data.cu_serial]
                if data.dmm_serial:
                    record_serials.extend([data.dmm_serial, data.dmm_seal_serial, data.pink_paper_seal_serial])
                
                for serial in record_serials:
                    if serial in seen_serials:
                        batch_duplicates.add(serial)
                    seen_serials.add(serial)
                    all_serials.add(serial)
            
            # Check for duplicates within batch
            if batch_duplicates:
                duplicates_list = sorted(list(batch_duplicates))
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate serial numbers found within batch: {', '.join(duplicates_list)}"
                )
            
            # Check for duplicates in database (chunked for performance)
            chunk_size = 1000
            serial_list = list(all_serials)
            existing_serials = set()
            
            for i in range(0, len(serial_list), chunk_size):
                chunk = serial_list[i:i + chunk_size]
                existing_in_chunk = session.query(EVMComponent.serial_number).filter(
                    EVMComponent.serial_number.in_(chunk)
                ).all()
                existing_serials.update([serial[0] for serial in existing_in_chunk])
            
            if existing_serials:
                duplicates_list = sorted(list(existing_serials))
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate serial numbers found in database: {', '.join(duplicates_list)}"
                )
            
            # Prepare box assignments and mappings
            box_assignments = {}
            component_box_map = {}
            all_cu_serials = set()
            
            for data in data_list:
                box_assignments[data.box_no] = box_assignments.get(data.box_no, 0) + 1
                component_box_map[data.cu_serial] = data.box_no
                all_cu_serials.add(data.cu_serial)
                
                if data.dmm_serial:
                    component_box_map[data.dmm_serial] = data.box_no
                    component_box_map[data.dmm_seal_serial] = data.box_no
                    component_box_map[data.pink_paper_seal_serial] = data.box_no
            
            validate_and_prepare_boxes(session, box_assignments)
            validate_component_box_assignment(session, all_serials, component_box_map)
            
            deo_user_id = get_deo_user_id(session, user_id)
            flc_records = []
            
            for data in data_list:
                pairing_id = None
                
                # Create pairing only for complete CU records
                if data.dmm_serial:
                    pairing = PairingRecord(created_by_id=user_id)
                    session.add(pairing)
                    session.flush()
                    pairing_id = pairing.id
                    
                    pairing_log = PairingRecordLogs(
                        evm_id=None,
                        polling_station_id=None,
                        created_by_id=user_id,
                        completed_by_id=None,
                        completed_at=None
                    )
                    session.add(pairing_log)
                    session.flush()
                
                # Create CU component
                cu, cu_log = create_or_update_component_safe(
                    session, data.cu_serial, EVMComponentType.CU, 
                    data.cu_dom, data.box_no, deo_user_id, data.passed, pairing_id
                )
                
                # Initialize optional components
                dmm = dmm_log = dmm_seal = dmm_seal_log = pink_seal = pink_seal_log = None
                
                # Create optional components if provided
                if data.dmm_serial:
                    dmm, dmm_log = create_or_update_component_safe(
                        session, data.dmm_serial, EVMComponentType.DMM, 
                        data.dmm_dom, data.box_no, deo_user_id, data.passed, pairing_id
                    )
                    dmm_seal, dmm_seal_log = create_or_update_component_safe(
                        session, data.dmm_seal_serial, EVMComponentType.DMM_SEAL, 
                        None, data.box_no, deo_user_id, data.passed, pairing_id
                    )
                    pink_seal, pink_seal_log = create_or_update_component_safe(
                        session, data.pink_paper_seal_serial, EVMComponentType.PINK_PAPER_SEAL, 
                        None, data.box_no, deo_user_id, data.passed, pairing_id
                    )
                
                # Create FLC record
                flc = FLCRecord(
                    cu_id=cu.id,
                    dmm_id=dmm.id if dmm else None,
                    dmm_seal_id=dmm_seal.id if dmm_seal else None,
                    pink_paper_seal_id=pink_seal.id if pink_seal else None,
                    box_no=data.box_no,
                    passed=data.passed,
                    remarks=data.remarks,
                    flc_by_id=user_id
                )
                flc_records.append(flc)
                
                # Set log IDs
                flc.cu_log_id = cu_log.id
                flc.dmm_log_id = dmm_log.id if dmm_log else None
                flc.dmm_seal_log_id = dmm_seal_log.id if dmm_seal_log else None
                flc.pink_paper_seal_log_id = pink_seal_log.id if pink_seal_log else None
            
            session.add_all(flc_records)
            session.flush()
            
            create_cu_flc_logs_simple(session, flc_records, user_id)
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
            # Collect all BU serials for duplicate validation
            all_bu_serials = set()
            seen_serials = set()
            batch_duplicates = set()
            
            for data in data_list:
                if data.bu_serial in seen_serials:
                    batch_duplicates.add(data.bu_serial)
                seen_serials.add(data.bu_serial)
                all_bu_serials.add(data.bu_serial)
            
            # Check for duplicates within batch
            if batch_duplicates:
                duplicates_list = sorted(list(batch_duplicates))
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate BU serial numbers found within batch: {', '.join(duplicates_list)}"
                )
            
            # Check for duplicates in database (chunked for performance)
            chunk_size = 1000
            serial_list = list(all_bu_serials)
            existing_serials = set()
            
            for i in range(0, len(serial_list), chunk_size):
                chunk = serial_list[i:i + chunk_size]
                existing_in_chunk = session.query(EVMComponent.serial_number).filter(
                    EVMComponent.serial_number.in_(chunk),
                    EVMComponent.component_type == EVMComponentType.BU
                ).all()
                existing_serials.update([serial[0] for serial in existing_in_chunk])
            
            if existing_serials:
                duplicates_list = sorted(list(existing_serials))
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate BU serial numbers found in database: {', '.join(duplicates_list)}"
                )
            
            # Prepare box assignments and mappings
            box_assignments = {}
            component_box_map = {}
            
            for data in data_list:
                box_assignments[data.box_no] = box_assignments.get(data.box_no, 0) + 1
                component_box_map[data.bu_serial] = data.box_no
            
            validate_and_prepare_boxes(session, box_assignments)
            validate_component_box_assignment(session, all_bu_serials, component_box_map)
            
            deo_user_id = get_deo_user_id(session, user_id)
            flc_records = []
            
            for data in data_list:
                bu, bu_log = create_or_update_component_safe(
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
                flc.bu_log_id = bu_log.id
                flc_records.append(flc)
            
            session.add_all(flc_records)
            session.flush()
            
            create_bu_flc_logs(session, flc_records, user_id)
            update_box_counts(session, box_assignments)
            session.commit()
            
            return Response(status_code=200, content="FLC processing completed successfully")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FLC BU error: {e}")
        raise HTTPException(status_code=500, detail="FLC processing failed")

def flc_dmm(data_list: List[FLCDMMModel], user_id: int, background_tasks: BackgroundTasks):
    if not data_list:
        raise HTTPException(status_code=400, detail="No data provided")
    
    try:
        with Database.get_session() as session:
            # Collect all DMM serials for duplicate validation
            all_dmm_serials = set()
            seen_serials = set()
            batch_duplicates = set()
            
            for data in data_list:
                if data.dmm_serial in seen_serials:
                    batch_duplicates.add(data.dmm_serial)
                seen_serials.add(data.dmm_serial)
                all_dmm_serials.add(data.dmm_serial)
            
            # Check for duplicates within batch
            if batch_duplicates:
                duplicates_list = sorted(list(batch_duplicates))
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate DMM serial numbers found within batch: {', '.join(duplicates_list)}"
                )
            
            # Check for duplicates in database (chunked for performance)
            chunk_size = 1000
            serial_list = list(all_dmm_serials)
            existing_serials = set()
            
            for i in range(0, len(serial_list), chunk_size):
                chunk = serial_list[i:i + chunk_size]
                existing_in_chunk = session.query(EVMComponent.serial_number).filter(
                    EVMComponent.serial_number.in_(chunk),
                    EVMComponent.component_type == EVMComponentType.DMM
                ).all()
                existing_serials.update([serial[0] for serial in existing_in_chunk])
            
            if existing_serials:
                duplicates_list = sorted(list(existing_serials))
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate DMM serial numbers found in database: {', '.join(duplicates_list)}"
                )
            
            deo_user_id = get_deo_user_id(session, user_id)
            flc_records = []
            
            for data in data_list:
                dmm, dmm_log = create_or_update_component_safe(
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


def generate_dmm_flc_pdf(district_id: int, background_tasks: BackgroundTasks):
    try:
        with Database.get_session() as session:
  
            flc_records = session.query(FLCDMMUnit, EVMComponent.serial_number, EVMComponent.date_of_receipt)\
                .join(User, FLCDMMUnit.flc_by_id == User.id)\
                .join(EVMComponent, FLCDMMUnit.dmm_id == EVMComponent.id)\
                .filter(User.district_id == district_id)\
                .all()
            
            if not flc_records:
                raise HTTPException(status_code=404, detail="No DMM FLC records found for this district")
            
      
            pdf_data = [{
                "cu_number": "",
                "dmm_number": record[1] or "",  
                "dmm_seal_no": "",
                "cu_pink_seal": "",
                "passed": record[0].passed,
                "date_of_receipt": record[2]  
            } for record in flc_records]
            
            pdf_filename = FLC_Certificate_CU(pdf_data)
            background_tasks.add_task(remove_file, pdf_filename)
            return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DMM PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")


def generate_bu_flc_pdf(district_id: int, background_tasks: BackgroundTasks):
    try:
        with Database.get_session() as session:

            flc_records = session.query(FLCBallotUnit, EVMComponent.serial_number, EVMComponent.date_of_receipt)\
                .join(User, FLCBallotUnit.flc_by_id == User.id)\
                .join(EVMComponent, FLCBallotUnit.bu_id == EVMComponent.id)\
                .filter(User.district_id == district_id)\
                .all()
            
            if not flc_records:
                raise HTTPException(status_code=404, detail="No BU FLC records found for this district")
      
            pdf_data = [{
                "serial_number": record[1] or "",  
                "passed": record[0].passed,
                "date_of_receipt": record[2] 
            } for record in flc_records]
            
            pdf_filename = FLC_Certificate_BU(pdf_data)
            background_tasks.add_task(remove_file, pdf_filename)
            return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BU PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")


def generate_cu_flc_pdf(district_id: int, background_tasks: BackgroundTasks):
    try:
        with Database.get_session() as session:
   
            CU = aliased(EVMComponent)
            DMM = aliased(EVMComponent) 
            DMMSeal = aliased(EVMComponent)
            PinkSeal = aliased(EVMComponent)
            
         
            flc_records = session.query(
                FLCRecord,
                CU.serial_number.label('cu_serial'),
                CU.date_of_receipt.label('cu_date'),
                DMM.serial_number.label('dmm_serial'),
                DMM.date_of_receipt.label('dmm_date'),
                DMMSeal.serial_number.label('dmm_seal_serial'),
                DMMSeal.date_of_receipt.label('dmm_seal_date'),
                PinkSeal.serial_number.label('pink_seal_serial'),
                PinkSeal.date_of_receipt.label('pink_seal_date')
            )\
            .join(User, FLCRecord.flc_by_id == User.id)\
            .join(CU, FLCRecord.cu_id == CU.id)\
            .join(DMM, FLCRecord.dmm_id == DMM.id)\
            .outerjoin(DMMSeal, FLCRecord.dmm_seal_id == DMMSeal.id)\
            .outerjoin(PinkSeal, FLCRecord.pink_paper_seal_id == PinkSeal.id)\
            .filter(User.district_id == district_id)\
            .all()
            
            if not flc_records:
                raise HTTPException(status_code=404, detail="No CU FLC records found for this district")
            
       
            pdf_data = []
            for record in flc_records:
                flc, cu_serial, cu_date, dmm_serial, dmm_date, dmm_seal_serial, dmm_seal_date, pink_seal_serial, pink_seal_date = record
    
                receipt_date = cu_date or dmm_date or dmm_seal_date or pink_seal_date
                
                pdf_data.append({
                    "cu_number": cu_serial or "",
                    "dmm_number": dmm_serial or "",
                    "dmm_seal_no": dmm_seal_serial or "",
                    "cu_pink_seal": pink_seal_serial or "",
                    "passed": flc.passed,
                    "date_of_receipt": receipt_date
                })
            
            pdf_filename = FLC_Certificate_CU(pdf_data)
            background_tasks.add_task(remove_file, pdf_filename)
            return FileResponse(pdf_filename, media_type='application/pdf', filename=pdf_filename)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CU PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

def view_flc_components(component_type: str, district_id: int):
    with Database.get_session() as session:
        flc_records = []
        
        if component_type == "CU":
            records = session.query(FLCRecord).join(
                EVMComponent, FLCRecord.cu_id == EVMComponent.id
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).filter(
                and_(
                    FLCRecord.cu_id.isnot(None),
                    User.district_id == district_id
                )
            ).all()
            
            flc_records = [
                {
                    "id": record.id,
                    "serial_number": record.cu.serial_number if record.cu else None,
                    "component_type": "CU",
                    "flc_date": record.flc_date,
                    "status": "Passed" if record.passed else "Failed",
                    "remarks": record.remarks,
                    "flc_by": record.flc_by.username if record.flc_by else None,
                    "box_no": record.box_no,
                    "district_id": district_id
                } for record in records
            ]
            
        elif component_type == "BU":
            records = session.query(FLCBallotUnit).join(
                EVMComponent, FLCBallotUnit.bu_id == EVMComponent.id
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).filter(
                User.district_id == district_id
            ).all()
            
            flc_records = [
                {
                    "id": record.id,
                    "serial_number": record.bu.serial_number if record.bu else None,
                    "component_type": "BU",
                    "flc_date": record.flc_date,
                    "status": "Passed" if record.passed else "Failed",
                    "remarks": record.remarks,
                    "flc_by": record.flc_by.username if record.flc_by else None,
                    "box_no": record.box_no,
                    "district_id": district_id
                } for record in records
            ]
            
        elif component_type == "DMM":
            flc_dmm_records = session.query(FLCRecord).join(
                EVMComponent, FLCRecord.dmm_id == EVMComponent.id
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).filter(
                User.district_id == district_id
            ).all()
            
            flc_dmm_unit_records = session.query(FLCDMMUnit).join(
                EVMComponent, FLCDMMUnit.dmm_id == EVMComponent.id
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).filter(
                User.district_id == district_id
            ).all()
            
            flc_records.extend([
                {
                    "id": record.id,
                    "serial_number": record.dmm.serial_number if record.dmm else None,
                    "component_type": "DMM",
                    "flc_date": record.flc_date,
                    "status": "Passed" if record.passed else "Failed",
                    "remarks": record.remarks,
                    "flc_by": record.flc_by.username if record.flc_by else None,
                    "box_no": record.box_no} for record in flc_dmm_records])
        return flc_records
   
def view_all_districts_flc_summary() -> Dict[str, Any]:
    
    with Database.get_session() as session:
        districts = session.query(District).all()
        
        if not districts:
            raise HTTPException(status_code=204, detail="No districts found")
        
        # Initialize response structure similar to sec_dashboard
        response = {
            "CU": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
            "BU": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
            "totals": {
                "FLC_Pending": 0,
                "FLC_Passed": 0,
                "FLC_Failed": 0
            },
            "districts": []
        }
        
        for district in districts:
            # Query database directly for this district, joining with User to get district info
            district_results = session.query(
                EVMComponent.component_type,
                EVMComponent.status,
                func.count(EVMComponent.id).label('count')
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).filter(
                EVMComponent.component_type.in_(["CU", "BU"]),
                User.district_id == district.id
            ).group_by(
                EVMComponent.component_type,
                EVMComponent.status
            ).all()
            
            # Initialize district data structure
            district_data = {
                "district_id": district.id,
                "district_name": district.name,
                "CU": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
                "BU": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
                "totals": {
                    "FLC_Pending": 0,
                    "FLC_Passed": 0,
                    "FLC_Failed": 0
                }
            }
            
            # Process results using same logic as sec_dashboard
            for component_type, status, count in district_results:
                district_data[component_type]["total"] += count
                
                if status == "FLC_Passed":
                    district_data[component_type]["passed"] = count
                    district_data["totals"]["FLC_Passed"] += count
                elif status == "FLC_Failed":
                    district_data[component_type]["failed"] = count
                    district_data["totals"]["FLC_Failed"] += count
                elif status == "FLC_Pending":
                    district_data[component_type]["pending"] = count
                    district_data["totals"]["FLC_Pending"] += count
                
                # Update overall response totals
                response[component_type]["total"] += count
                
                if status == "FLC_Passed":
                    response[component_type]["passed"] += count
                    response["totals"]["FLC_Passed"] += count
                elif status == "FLC_Failed":
                    response[component_type]["failed"] += count
                    response["totals"]["FLC_Failed"] += count
                elif status == "FLC_Pending":
                    response[component_type]["pending"] += count
                    response["totals"]["FLC_Pending"] += count
            
            response["districts"].append(district_data)
        
        return response
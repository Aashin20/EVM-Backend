from models.evm import EVMComponent, EVMComponentType
from models.logs import EVMComponentLogs
from models.users import User,Warehouse
from .db import Database
from pydantic import BaseModel
from sqlalchemy import and_,or_,func
from typing import Optional, List,Dict, Any
from datetime import date,datetime
from annexure.Annex_1 import CU_1,DMM_1
from fastapi.responses import FileResponse
from fastapi import Response,BackgroundTasks
from models.users import LevelEnum
from fastapi.exceptions import HTTPException
from fastapi import HTTPException, Response
from sqlalchemy.orm import joinedload
from typing import List
from collections import defaultdict
import tempfile
import uuid
from utils.delete_file import remove_file


class ComponentModel(BaseModel):
    serial_number: str
    component_type: str
    dom: Optional[str]
    box_no: Optional[str] = None
    current_warehouse_id: Optional[int] = None #Remove for prod


def new_components(components: List[ComponentModel], phy_order_no: str, user_id: int,background_tasks: BackgroundTasks):
    failed_serials = []
    
    with Database.get_session() as session:
        to_add = []
        seen_serials = set()
        
        # Get current user and validate
        current_user = session.query(User).filter(User.id == user_id).first()
        
        district_name = current_user.district.name if current_user.district else ""
            
        for component in components:
            if component.component_type not in EVMComponentType.__members__:
                failed_serials.append(component.serial_number)
                continue
            
            if component.serial_number in seen_serials:
                failed_serials.append(component.serial_number)
                continue
            
            existing = session.query(EVMComponent).filter(
                EVMComponent.serial_number == component.serial_number
            ).first()
            
            if existing:
                failed_serials.append(component.serial_number)
                continue
            
            seen_serials.add(component.serial_number)
            
            new_component = EVMComponent(
                serial_number=component.serial_number,
                component_type=EVMComponentType[component.component_type],
                dom=component.dom,
                box_no=component.box_no,
                current_warehouse_id=component.current_warehouse_id,
                current_user_id=3,
                last_received_from_id = 3,
                date_of_receipt=datetime.now()
            )
            to_add.append(new_component)
        
        if failed_serials:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to process components with serial numbers: {', '.join(failed_serials)}"
            )
        
        if not to_add:
            raise HTTPException(status_code=400, detail="No valid components to add")
        
        # Fetch warehouse names for all components
        warehouse_ids = {str(comp.current_warehouse_id) for comp in to_add if comp.current_warehouse_id is not None}
        warehouse_names = {}
        
        if warehouse_ids:
            warehouses = session.query(Warehouse).filter(Warehouse.id.in_(warehouse_ids)).all()
            warehouse_names = {w.id: w.name for w in warehouses}
        
        # Add all components to the database
        session.add_all(to_add)
        session.commit()
        
        # CREATE LOGS - Add corresponding entries to logs table
        logs_to_add = []
        for component in to_add:
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
            logs_to_add.append(component_log)
        
        session.add_all(logs_to_add)
        session.commit()
        
        # Generate PDF - validate component type
        component_type = components[0].component_type if components else None
        
            
        if component_type in ["CU", "BU"]:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            CU_1(
                    components=to_add, 
                    component_type=component_type, 
                    warehouse_names=warehouse_names, 
                    filename=tmp_path,
                    alloted_to=district_name,
                    order_no=phy_order_no
                )
            
            background_tasks.add_task(remove_file, tmp_path)

            return FileResponse(
                    path=tmp_path,
                    filename=f"Annexure_1_{component_type}_{uuid.uuid4().hex}.pdf",
                    media_type="application/pdf"
                )

        else:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            DMM_1(
                    components=to_add, 
                    component_type=component_type, 
                    filename=tmp_path,
                    alloted_to=district_name,
                    order_no=phy_order_no
                )

            background_tasks.add_task(remove_file, tmp_path)

            return FileResponse(
                    path=tmp_path,
                    filename=f"Annexure_1_{component_type}_{uuid.uuid4().hex}.pdf",
                    media_type="application/pdf"
                )
    
def view_components(component_type:str,user_id: int):

    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.current_user_id == user_id,
                EVMComponent.component_type == component_type,
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "district_id": component.current_user.district_id,
                "local_body_name": component.current_user.local_body.name if component.current_user and component.current_user.local_body else None,
                "current_user": component.current_user.username if component.current_user else None,
                "warehouse_id": component.current_warehouse_id,
                "status": component.status
            } for component in components
        ]
    

def view_paired_cu(user_id: int):
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.current_user_id == user_id,
                EVMComponent.component_type == "CU",
                EVMComponent.pairing_id.isnot(None),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "warehouse_id": component.current_warehouse_id,
                "paired_components": [
                    {
                        "id": paired_component.id,
                        "component_type": paired_component.component_type,
                        "serial_number": paired_component.serial_number,
                    } 
                    for paired_component in component.pairing.components
                    if paired_component.id != component.id

                ]
            } for component in components
        ]
    

def view_paired_bu(user_id:int):
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.current_user_id == user_id,
                EVMComponent.component_type == "BU",
                EVMComponent.status.in_(["FLC_Passed", "FLC_Failed"]),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "warehouse_id": component.current_warehouse_id,
            } for component in components
        ]


def dashboard_all(user_id: int) -> Dict[str, Any]:
    with Database.get_session() as session:
        
        results = session.query(
            EVMComponent.component_type,
            EVMComponent.status,
            func.count(EVMComponent.id).label('count')
        ).filter(
            EVMComponent.current_user_id == user_id,
            EVMComponent.component_type.in_(["CU", "DMM", "BU"])
        ).group_by(
            EVMComponent.component_type,
            EVMComponent.status
        ).all()
        
        
        response = {
            "CU": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
            "DMM": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
            "BU": {"total": 0, "passed": 0, "failed": 0, "pending": 0},
            "totals": {
                "FLC_Pending": 0,
                "FLC_Passed": 0,
                "FLC_Failed": 0
            }
        }
        
        
        for component_type, status, count in results:
            response[component_type]["total"] += count
            
            if status == "FLC_Passed":
                response[component_type]["passed"] = count
                response["totals"]["FLC_Passed"] += count
            elif status == "FLC_Failed":
                response[component_type]["failed"] = count
                response["totals"]["FLC_Failed"] += count
            elif status == "FLC_Pending":
                response[component_type]["pending"] = count
                response["totals"]["FLC_Pending"] += count
        
        return response


def view_paired_cu_sec():
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.component_type == "CU",
                EVMComponent.pairing_id.isnot(None),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "district_name": component.current_user.district.name if component.current_user and component.current_user.district else None,
                "paired_components": [
                    {
                        "id": paired_component.id,
                        "component_type": paired_component.component_type,
                        "serial_number": paired_component.serial_number,
                    } 
                    for paired_component in component.pairing.components
                    if paired_component.id != component.id

                ]
            } for component in components
        ]

def view_paired_cu_deo(district_id: int):
    with Database.get_session() as session:
        components = session.query(EVMComponent).join(
            User, EVMComponent.current_user_id == User.id
        ).filter(
            and_(
                User.district_id == district_id,
                EVMComponent.component_type == "CU",
                EVMComponent.pairing_id.isnot(None),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "district_name": component.current_user.district.name if component.current_user and component.current_user.district else None,
                "paired_components": [
                    {
                        "id": paired_component.id,
                        "component_type": paired_component.component_type,
                        "serial_number": paired_component.serial_number,
                    } 
                    for paired_component in component.pairing.components
                    if paired_component.id != component.id

                ]
            } for component in components
        ]
    

    
def view_paired_bu_sec():
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.component_type == "BU",
                EVMComponent.status.in_(["FLC_Passed", "FLC_Failed"]),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "district_name": component.current_user.district.name if component.current_user and component.current_user.district else None,
            } for component in components
        ]
    
def view_paired_bu_deo(district_id:int):
    with Database.get_session() as session:
        components = session.query(EVMComponent).join(
            User, EVMComponent.current_user_id == User.id
        ).filter(
            and_(
                User.district_id == district_id,
                EVMComponent.component_type == "BU",
                EVMComponent.status.in_(["FLC_Passed", "FLC_Failed"]),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "district_name": component.current_user.district.name if component.current_user and component.current_user.district else None,
            } for component in components
        ]

def view_components_sec(component_type:str):
    component_type = component_type.upper()
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.component_type == component_type,
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "district_name": component.current_user.district.name if component.current_user and component.current_user.district else None,
                "local_body_name": component.current_user.local_body.name if component.current_user and component.current_user.local_body else None,
                "current_user": component.current_user.username if component.current_user else None,
                "status": component.status
            } for component in components
        ]
    
def view_components_deo(component_type:str,district_id:int):
    with Database.get_session() as session:
        components = session.query(EVMComponent).join(
            User, EVMComponent.current_user_id == User.id
        ).filter(
            and_(
                User.district_id == district_id,
                EVMComponent.component_type == component_type,
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "district_name": component.current_user.district.name if component.current_user and component.current_user.district else None,
                "local_body_name": component.current_user.local_body.name if component.current_user and component.current_user.local_body else None,
                "current_user": component.current_user.username if component.current_user else None,
                "warehouse_name": component.current_warehouse.name if component.current_warehouse else None,
                "status": component.status
            } for component in components
        ]
    


def approve_component_by_sec(serial_numbers: List[str]):
    if not serial_numbers:
        raise HTTPException(status_code=400, detail="No serial numbers provided.")

    with Database.get_session() as db:
 
        component = db.query(EVMComponent).options(
            joinedload(EVMComponent.current_warehouse)
        ).filter(
            EVMComponent.serial_number == serial_numbers[0]
        ).first()

        if not component or not component.current_warehouse:
            raise HTTPException(status_code=404, detail="Component or warehouse not found.")

        district_id = component.current_warehouse.district_id

      
        deo = db.query(User).filter(
            User.district_id == district_id,
            User.role.has(name='DEO') 
        ).first()

        if not deo:
            raise HTTPException(status_code=404, detail="DEO not found in the district.")

    
        components = db.query(EVMComponent).filter(
            EVMComponent.serial_number.in_(serial_numbers)
        ).all()

        for comp in components:
            comp.is_sec_approved = True
            comp.current_user_id=deo.id

        db.commit()

        return Response(status_code=200)




def approval_queue_sec():
    with Database.get_session() as db:
     
        pending_components = db.query(EVMComponent).options(
            joinedload(EVMComponent.current_warehouse).joinedload(Warehouse.district)
        ).filter(
            EVMComponent.is_sec_approved == False,
            EVMComponent.component_type.notin_([
                EVMComponentType.DMM_SEAL,
                EVMComponentType.PINK_PAPER_SEAL
            ])
        ).all()

      
        grouped = defaultdict(list)

        for comp in pending_components:
            warehouse = comp.current_warehouse
            district = warehouse.district if warehouse else None
            if not district:
                continue 

            grouped[district.name].append({
                "component_type": comp.component_type.value,
                "serial_number": comp.serial_number,
                "box_no": comp.box_no
            })

     
        result = []
        for district_name, comps in grouped.items():
            result.append({
                "district": district_name,
                "components": comps
            })

        return result

def view_dmm(user_id: int):
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(
            and_(
                EVMComponent.current_user_id == user_id,
                EVMComponent.component_type == "DMM",
                EVMComponent.pairing_id.is_(None), 
                EVMComponent.status.in_(["FLC_Passed"]),
            )
        ).all()
        if not components:
            raise HTTPException(status_code=204)
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "status": component.status
            } for component in components
        ]
    

def warehouse_reentry(warehouse_updates: List[Dict[str, Any]], user_id: int):
    
    with Database.get_session() as db:
        try:
            total_updated = 0
            
            # Process each warehouse update group
            for update_group in warehouse_updates:
                warehouse_id = update_group.get("warehouse")
                serial_numbers = update_group.get("serial", [])
                
                if not serial_numbers:
                    continue
                
                # Check if all serial numbers exist
                existing_components = db.query(EVMComponent).filter(
                    EVMComponent.serial_number.in_(serial_numbers)
                ).all()
                
                existing_serials = {comp.serial_number for comp in existing_components}
                missing_serials = set(serial_numbers) - existing_serials
                
                if missing_serials:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Serial numbers not found: {list(missing_serials)}"
                    )
                
                # Create audit log entries for each component before updating
                for component in existing_components:
                    audit_entry = EVMComponentLogs(
                        serial_number=component.serial_number,
                        component_type=component.component_type,
                        status=component.status,
                        is_verified=component.is_verified,
                        dom=component.dom,
                        box_no=component.box_no,
                        current_user_id=user_id,
                        current_warehouse_id=warehouse_id,
                        pairing_id=component.pairing_id
                    )
                    db.add(audit_entry)
                
                # Update warehouse for all components in this group
                updated_count = db.query(EVMComponent).filter(
                    EVMComponent.serial_number.in_(serial_numbers)
                ).update(
                    {EVMComponent.current_warehouse_id: warehouse_id},
                    synchronize_session=False
                )
                
                total_updated += updated_count
            
            # Commit all changes
            db.commit()
            
            return {"message": "Warehouse updated successfully", "components_updated": total_updated}

            
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update EVM warehouse: {str(e)}"
            )

def components_without_warehouse(district_id: int):
    with Database.get_session() as db:
        try:
            result = {"CU": [], "BU": [], "DMM": []}

  
            cu_boxes = (
                db.query(EVMComponent.box_no)
                .join(User, EVMComponent.current_user_id == User.id)
                .filter(
                    EVMComponent.component_type == "CU",
                    EVMComponent.status == "FLC_Passed",
                    EVMComponent.current_warehouse_id == None,
                    EVMComponent.box_no != None,
                    User.district_id == district_id
                )
                .distinct()
                .all()
            )
            result["CU"] = [row.box_no for row in cu_boxes]

       
            bu_boxes = (
                db.query(EVMComponent.box_no)
                .join(User, EVMComponent.current_user_id == User.id)
                .filter(
                    EVMComponent.component_type == "BU",
                    EVMComponent.status == "FLC_Passed",
                    EVMComponent.current_warehouse_id == None,
                    EVMComponent.box_no != None,
                    User.district_id == district_id
                )
                .distinct()
                .all()
            )
            result["BU"] = [row.box_no for row in bu_boxes]

      
            dmm_serials = (
                db.query(EVMComponent.serial_number)
                .join(User, EVMComponent.current_user_id == User.id)
                .filter(
                    EVMComponent.component_type == "DMM",
                    EVMComponent.status == "FLC_Passed",
                    EVMComponent.current_warehouse_id == None,
                    EVMComponent.pairing_id == None,
                    User.district_id == district_id
                )
                .all()
            )
            result["DMM"] = [row.serial_number for row in dmm_serials]

            return result

        except Exception as e:
            print(f"Error fetching unallocated components: {str(e)}")
            return {"CU": [], "BU": [], "DMM": []}



def warehouse_box_entry(warehouse_updates: List[Dict[str, Any]], user_id: int):
    print(warehouse_updates,flush=True)
    with Database.get_session() as db:
        try:
            total_updated = 0
            for update_group in warehouse_updates:
                warehouse_id = update_group.get("warehouse")
                box_nos = update_group.get("box_nos", [])

                if not box_nos:
                    continue

                components = db.query(EVMComponent).filter(
                    EVMComponent.box_no.in_(box_nos)
                ).all()

                if not components:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No components found for boxes: {box_nos}"
                    )

        
                for component in components:
                    audit_entry = EVMComponentLogs(
                        serial_number=component.serial_number,
                        component_type=component.component_type,
                        status=component.status,
                        is_verified=component.is_verified,
                        dom=component.dom,
                        box_no=component.box_no,
                        current_user_id=user_id,
                        current_warehouse_id=warehouse_id,
                        pairing_id=component.pairing_id
                    )
                    db.add(audit_entry)

    
                updated_count = db.query(EVMComponent).filter(
                    EVMComponent.box_no.in_(box_nos)
                ).update(
                    {EVMComponent.current_warehouse_id: warehouse_id},
                    synchronize_session=False
                )

                total_updated += updated_count

            db.commit()
            return {"message": "Warehouse updated successfully", "components_updated": total_updated}

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update EVM warehouse: {str(e)}"
            )
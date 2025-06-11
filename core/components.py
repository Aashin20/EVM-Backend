from models.evm import EVMComponent, EVMComponentType
from models.logs import EVMComponentLogs
from models.users import User,Warehouse
from .db import Database
from pydantic import BaseModel
from sqlalchemy import and_,or_,func
from typing import Optional, List
from datetime import date,datetime
from annexure.Annex_1 import CU_1,DMM_1
from fastapi.responses import FileResponse
from fastapi import Response
from models.users import LevelEnum
from fastapi.exceptions import HTTPException

class ComponentModel(BaseModel):
    serial_number: str
    component_type: str
    dom: date
    box_no: int
    current_warehouse_id: Optional[int] = None #Remove for prod


def new_components(components: List[ComponentModel], phy_order_no: str, user_id: int):
    failed_serials = []
    
    with Database.get_session() as session:
        to_add = []
        seen_serials = set()
        
        # Get current user and validate
        current_user = session.query(User).filter(User.id == user_id).first()
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        
        district_name = current_user.district.name
            
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
                current_user_id=user_id,
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
        if not component_type:
            raise HTTPException(status_code=400, detail="Component type is required")
            
        if component_type in ["CU", "BU"]:
            pdf_filename = f"Annexure_1_{component_type}.pdf"
            
            CU_1(
                components=to_add, 
                component_type=component_type, 
                warehouse_names=warehouse_names, 
                filename=pdf_filename,
                alloted_to=district_name,
                order_no=phy_order_no
            )
            
            return FileResponse(
                path=pdf_filename,
                filename=pdf_filename,
                media_type="application/pdf"
            )
        else:
            pdf_filename = f"Annexure_1_{component_type}.pdf"
            DMM_1(
                components=to_add, 
                component_type=component_type, 
                filename=pdf_filename,
                alloted_to=district_name,
                order_no=phy_order_no
            )
            return FileResponse(
                path=pdf_filename,
                filename=pdf_filename,
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
            return 204
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "district_id": component.current_user.district_id,
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
            return 204
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
            return 204
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


def get_details(user_id:int):
    with Database.get_session() as session:
        cu_count = session.query(EVMComponent).filter_by(current_user_id=user_id, component_type="CU").count()
        dmm_count = session.query(EVMComponent).filter_by(current_user_id=user_id, component_type="DMM").count()
        bu_count = session.query(EVMComponent).filter_by(current_user_id=user_id, component_type="BU").count()

        flc_pending = session.query(EVMComponent).filter_by(current_user_id=user_id, status="FLC_Pending").count()
        flc_passed = session.query(EVMComponent).filter_by(current_user_id=user_id, status="FLC_Passed").count()
        flc_failed = session.query(EVMComponent).filter_by(current_user_id=user_id, status="FLC_Failed").count()

        return {
            "CU": cu_count,
            "DMM": dmm_count,
            "BU": bu_count,
            "FLC_Pending": flc_pending,
            "FLC_Passed": flc_passed,
            "FLC_Failed": flc_failed
        }
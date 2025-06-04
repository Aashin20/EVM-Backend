from models.evm import EVMComponent, Allotment, AllotmentItem, FLCRecord, FLCBallotUnit, EVMComponentType
from models.users import User
from .db import Database
from pydantic import BaseModel
from sqlalchemy import and_
from typing import Optional, List
from datetime import date

class ComponentModel(BaseModel):
    serial_number: str
    component_type: str
    dom: date
    box_no: int
    current_warehouse_id: Optional[int] = None #Remove for prod
    user_id: int #Remove for prod


def new_components(components: List[ComponentModel]):
    failed_serials = []
    
    with Database.get_session() as session:
        to_add = []
        seen_serials = set()
        
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
                current_user_id=component.user_id
            )
            to_add.append(new_component)
        
   
        if failed_serials:
            return {
                "status": "error",
                "returns": failed_serials
            }
        
  
        session.add_all(to_add)
        session.commit()
        
        return {
            "status": "200",
            "returns": []
        }
    
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
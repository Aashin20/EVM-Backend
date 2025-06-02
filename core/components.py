from models.evm import EVMComponent, Allotment, AllotmentItem, FLCRecord, FLCBallotUnit, EVMComponentType
from models.users import User
from .db import Database
from pydantic import BaseModel
from sqlalchemy import and_

class ComponentModel(BaseModel):
    serial_number: str
    component_type: str
    user_id: int

def new_component(component: ComponentModel):
    if component.component_type not in EVMComponentType:
        return {"error": "Invalid component type"}
    with Database.get_session() as session:
        existing = session.query(EVMComponent).filter(EVMComponent.serial_number == component.serial_number).first()
        if existing:
            return {"error": "Component with this serial number already exists"}
        new_component = EVMComponent(
            serial_number=component.serial_number,
            component_type=EVMComponentType(component.component_type),
            current_user_id=component.user_id
        )
        session.add(new_component)
        session.commit()
        return {"message": "Component added successfully", "component_id": new_component.id}
    
def view_cu(district_id:int):

    with Database.get_session() as session:
        components = session.query(EVMComponent)\
            .join(EVMComponent.current_user)\
            .filter(
                and_(
                    User.district_id == district_id,
                    EVMComponent.component_type == "CU"
                )
            ).all()
        if not components:
            return {"message": "No components found for this district"}
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "warehouse_id": component.current_warehouse_id,
            } for component in components
        ]
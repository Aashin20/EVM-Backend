from models.evm import EVMComponent, Allotment, AllotmentItem, FLCRecord, FLCBallotUnit, EVMComponentType
from models.users import User
from .db import Database
from pydantic import BaseModel

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
    

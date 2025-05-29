from models.evm import EVMComponent, Allotment, AllotmentItem, FLCRecord, FLCBallotUnit, EVMComponentType
from models.users import User
from .db import Database
from pydantic import BaseModel

class ComponentModel(BaseModel):
    serial_number: str
    component_type: str
    user_id: int


from models.evm import AllotmentItem, FLCRecord, FLCBallotUnit,Allotment,EVMComponent
from core.db import Database
from pydantic import BaseModel
from typing import Optional,List
from models.evm import AllotmentType
from fastapi.exceptions import HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo

class AllotmentModel(BaseModel):
    allotment_type: AllotmentType
    from_user_id: Optional[int] = None  #Remove for prod
    from_local_body_id: Optional[int] = None #Remove for prod
    from_district_id: Optional[int] = None  #Remove for prod

    to_user_id: int
    evm_component_ids: List[int]
    to_local_body_id: Optional[int] = None
    to_district_id: Optional[int] = None
    original_allotment_id: Optional[int] = None
    return_reason: Optional[str] = None


class AllotmentResponse(BaseModel):
    id: int
    allotment_type: str
    from_user_id: Optional[int]
    to_user_id: int
    status: str
    evm_component_ids: List[int]

    class Config:
        orm_mode = True

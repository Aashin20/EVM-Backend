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

def create_allotment(data: AllotmentModel):
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(EVMComponent.id.in_(data.evm_component_ids)).all()
        if len(components) != len(data.evm_component_ids):
            raise HTTPException(status_code=404, detail="One or more EVM components not found.")
        
        for comp in components:
            if comp.status in ["used", "returned", "flc_failed", "faulty"]:
                raise HTTPException(400, f"Component {comp.serial_number} is not available for allotment.")
            if comp.current_user_id != data.from_user_id:
                raise HTTPException(status_code=403, detail=f"Component {comp.serial_number} is not owned by the sender.")

        allotment = Allotment(
            allotment_type=data.allotment_type.value,
            from_user_id=data.from_user_id,
            to_user_id=data.to_user_id,
            from_local_body_id=data.from_local_body_id,
            to_local_body_id=data.to_local_body_id,
            from_district_id=data.from_district_id,
            to_district_id=data.to_district_id,
            initiated_by_id=data.from_user_id,  #Fix for prod
            is_return=(data.allotment_type.value == "Return"),
            return_reason=data.return_reason,
            original_allotment_id=data.original_allotment_id
        )
        session.add(allotment)
        session.commit()
        session.refresh(allotment)

        for component in components:
            item = AllotmentItem(
                allotment_id=allotment.id,
                evm_component_id=component.id
            )
            session.add(item)

        session.commit()
        return {
            "id": allotment.id,
            "allotment_type": allotment.allotment_type.value,
            "from_user_id": allotment.from_user_id,
            "to_user_id": allotment.to_user_id,
            "status": allotment.status,
            "evm_component_ids": data.evm_component_ids
        }


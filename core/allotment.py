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


def create_allotment(data: AllotmentModel):
    with Database.get_session() as session:
        components = session.query(EVMComponent).filter(EVMComponent.id.in_(data.evm_component_ids)).all()
        if len(components) != len(data.evm_component_ids):
            raise HTTPException(status_code=404, detail="One or more EVM components not found.")
        
        for comp in components:
            if comp.status in ["Polled","Counted","FLC_Pending", "FLC_Failed", "Faulty"]:
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


def approve_allotment(allotment_id: int, approver_id: int):
    
    with Database.get_session() as db:    

        allotment = db.query(Allotment).filter(Allotment.id == allotment_id).first()

        if not allotment:
            raise HTTPException(status_code=404, detail="Allotment not found.")

        if allotment.status == "approved":
            raise HTTPException(status_code=400, detail="Allotment already approved.")

        if allotment.status == "rejected":
            raise HTTPException(status_code=400, detail="Cannot approve a rejected allotment.")


        
        allotment.approved_by_id = approver_id
        allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))

    
        for item in allotment.items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if component:
                component.current_user_id = allotment.to_user_id
                component.status = "allocated"
                component.is_allocated = True

        db.commit()
        db.refresh(allotment)

        return {
            "message": "Allotment approved successfully.",
            "allotment_id": allotment.id,
            "approved_at": allotment.approved_at.isoformat()
        }
    

"""
Stage	Status	When to set it
Created in stock	FLC Pending	Default value
After pairing is done	paired	After FLC pairing
After final allotment (RO→PO)	allocated_final	Allotted to PO
During polling	used	PO used it for election
Return flow initiated	return_pending	PO → RO/BO during returns
Returned successfully	returned	After inspection
Failed in FLC	flc_failed	Not passed FLC
Damaged	faulty	Marked manually
"""
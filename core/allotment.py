from models.evm import AllotmentItem, FLCRecord, FLCBallotUnit,Allotment,EVMComponent
from models.users import User
from core.db import Database
from pydantic import BaseModel
from typing import Optional,List
from models.evm import AllotmentType, PollingStation
from fastapi.exceptions import HTTPException
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import joinedload
from models.evm import PairingRecord, EVMComponentType
from fastapi import Response
import traceback

class AllotmentModel(BaseModel):
    allotment_type: AllotmentType
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

class EVMCommissioningModel(BaseModel):
    evm_no: str
    cu_serial : str
    bu_serial : List[str]
    ps_no : int



def create_allotment(evm: AllotmentModel,from_user_id: int):  
    with Database.get_session() as db:
        components = db.query(EVMComponent).filter(
            EVMComponent.id.in_(evm.evm_component_ids)
        ).all()

        if len(components) != len(evm.evm_component_ids):
            raise HTTPException(status_code=404, detail="One or more EVM components not found.")

        for comp in components:
            if comp.status in ["Polled", "Counted", "FLC_Pending", "FLC_Failed", "Faulty"]:
                raise HTTPException(status_code=400, detail=f"Component {comp.serial_number} is not available.")
            if comp.current_user_id != from_user_id:
                raise HTTPException(status_code=403, detail=f"Component {comp.serial_number} is not owned by the sender.")

        allotment = Allotment(
            allotment_type=evm.allotment_type,
            from_user_id=from_user_id,
            to_user_id=evm.to_user_id,
            from_local_body_id=evm.from_local_body_id,
            to_local_body_id=evm.to_local_body_id,
            from_district_id=evm.from_district_id,
            to_district_id=evm.to_district_id,
            original_allotment_id=evm.original_allotment_id,
            return_reason=evm.return_reason,
            initiated_by_id=from_user_id,
            is_return=(evm.allotment_type == "RETURN"),
            status="pending"
        )
        db.add(allotment)
        db.commit()
        db.refresh(allotment)


        for comp in components:
            db.add(AllotmentItem(allotment_id=allotment.id, evm_component_id=comp.id))

        db.commit()
        return {
            "id": allotment.id,
            "allotment_type": allotment.allotment_type,
            "status": allotment.status,
            "evm_component_ids": evm.evm_component_ids
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

        # Fetch approver user to get warehouse_id
        approver = db.query(User).filter(User.id == approver_id).first()
        if not approver:
            raise HTTPException(status_code=404, detail="Approver not found.")

        allotment.status = "approved"
        allotment.approved_by_id = approver_id
        allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))

        for item in allotment.items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if not component:
                continue

            # Always update the directly allotted component
            component.current_user_id = allotment.to_user_id
            component.current_warehouse_id = approver.warehouse_id

            # If the component is part of a pairing, update all in the pair
            if component.pairing_id:
                paired_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == component.pairing_id
                ).all()
                for paired in paired_components:
                    paired.current_user_id = allotment.to_user_id
                    paired.current_warehouse_id = approver.warehouse_id
        db.commit()
        db.refresh(allotment)

        return {
            "message": "Allotment approved successfully.",
            "allotment_id": allotment.id,
            "approved_at": allotment.approved_at.isoformat(),
            "updated_components": [item.evm_component_id for item in allotment.items]
        }


def approval_queue(user_id: int):
    with Database.get_session() as session:
        pending_allotments = session.query(Allotment).filter(
            Allotment.approved_by_id.is_(None),
            Allotment.status == "pending",
            Allotment.to_user_id == user_id
        ).options(
            joinedload(Allotment.items)
                .joinedload(AllotmentItem.evm_component)
                .joinedload(EVMComponent.pairing)
                .joinedload(PairingRecord.components),
            joinedload(Allotment.from_district),
            joinedload(Allotment.to_district),
            joinedload(Allotment.from_local_body),
            joinedload(Allotment.to_local_body),
            joinedload(Allotment.from_user),
            joinedload(Allotment.to_user)
        ).all()

        if not pending_allotments:
            return {"message": "No pending allotments for approval."}

        return [
            {
                "id": allotment.id,
                "allotment_type": allotment.allotment_type,
                "from_user_id": allotment.from_user_id,
                "to_user_id": allotment.to_user_id,
                "from_district_id": allotment.from_district_id,
                "from_district_name": allotment.from_district.name if allotment.from_district else None,
                "to_district_id": allotment.to_district_id,
                "to_district_name": allotment.to_district.name if allotment.to_district else None,
                "from_local_body_id": allotment.from_local_body_id,
                "from_local_body_name": allotment.from_local_body.name if allotment.from_local_body else None,
                "to_local_body_id": allotment.to_local_body_id,
                "to_local_body_name": allotment.to_local_body.name if allotment.to_local_body else None,
                "components": [
                    {
                        "serial_number": item.evm_component.serial_number,
                        "component_type": item.evm_component.component_type,
                        "paired_components": [
                            {
                                "serial_number": paired_comp.serial_number,
                                "component_type": paired_comp.component_type,
                            }
                            for paired_comp in (item.evm_component.pairing.components if item.evm_component.pairing else [])
                            if paired_comp.id != item.evm_component.id
                        ] if item.evm_component.pairing else []
                    }
                    for item in allotment.items
                ],
                "created_at": allotment.created_at.isoformat()
            } for allotment in pending_allotments
        ]
    
def reject_allotment(allotment_id: int, approver_id: int):
    with Database.get_session() as db:
        allotment = db.query(Allotment).filter(Allotment.id == allotment_id).first()
        if not allotment:
            raise HTTPException(status_code=404, detail="Allotment not found.")
        if allotment.status == "approved":
            raise HTTPException(status_code=400, detail="Allotment already approved.")
        if allotment.status == "rejected":
            raise HTTPException(status_code=400, detail="Allotment already rejected.")

        approver = db.query(User).filter(User.id == approver_id).first()
        if not approver:
            raise HTTPException(status_code=404, detail="Approver not found.")

        # Just mark as rejected — don't update component ownership
        allotment.status = "rejected"
        allotment.approved_by_id = approver_id
        allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))

        db.commit()
        db.refresh(allotment)

        return Response(status_code=200)


from models.evm import (AllotmentItem, Allotment,EVMComponent,
                        AllotmentType, PollingStation,AllotmentItemPending,AllotmentPending)
from models.logs import AllotmentLogs,EVMComponentLogs,AllotmentItemLogs, PairingRecordLogs
from models.users import User,LocalBody,District,Warehouse
from core.db import Database
from pydantic import BaseModel
from typing import Optional,List
from fastapi.exceptions import HTTPException
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import joinedload
from sqlalchemy import and_
from models.evm import PairingRecord, EVMComponentType
from fastapi import Response
import traceback
from fastapi.responses import FileResponse


class AllotmentModel(BaseModel):
    allotment_type: AllotmentType
    from_local_body_id: Optional[str] = None #Remove for prod
    from_district_id: Optional[int] = None  #Remove for prod

    to_user_id: int
    evm_component_ids: List[int]
    to_local_body_id: Optional[str] = None
    to_district_id: Optional[int] = None
    original_allotment_id: Optional[int] = None
    reject_reason: Optional[str] = None
    is_temporary: Optional[bool] = False
    temporary_reason: Optional[str] = None
    temporary_allotted_to_name: Optional[str] = None


class AllotmentResponse(BaseModel):
    id: int
    allotment_type: str
    from_user_id: Optional[int]
    to_user_id: int
    status: str
    evm_component_ids: List[int]

        
def pending(evm: AllotmentModel, from_user_id: int):
    with Database.get_session() as db:
        # Same validations as create_allotment
        components = db.query(EVMComponent).filter(
            EVMComponent.id.in_(evm.evm_component_ids)
        ).all()

        for comp in components:
            if comp.status in ["Polled", "Counted", "FLC_Failed", "Faulty"]:
                raise HTTPException(status_code=400, detail=f"Component {comp.serial_number} is not available.")
            if comp.current_user_id != from_user_id:
                raise HTTPException(status_code=403, detail=f"Component {comp.serial_number} is not owned by the sender.")

        # Create the pending allotment
        allotment_pending = AllotmentPending(
            allotment_type=evm.allotment_type,
            from_user_id=from_user_id,
            to_user_id=evm.to_user_id,
            from_local_body_id=evm.from_local_body_id,  
            to_local_body_id=evm.to_local_body_id,      
            from_district_id=evm.from_district_id,      
            to_district_id=evm.to_district_id,         
            initiated_by_id=from_user_id,
            status="pending"
        )
        db.add(allotment_pending)
        db.commit()
        db.refresh(allotment_pending)

        # Create pending allotment items
        for comp in components:
            db.add(AllotmentItemPending(
                allotment_pending_id=allotment_pending.id, 
                evm_component_id=comp.id
            ))
            comp.status="FLC_Passed/Pending"

        db.commit()
        
        return {"status_code":200}

def view_pending_allotments(user_id: int):
    with Database.get_session() as db:
        from sqlalchemy.orm import joinedload
        
        pending_allotments = db.query(AllotmentPending).options(
            joinedload(AllotmentPending.from_local_body),
            joinedload(AllotmentPending.to_local_body),
            joinedload(AllotmentPending.from_district),
            joinedload(AllotmentPending.to_district),
            joinedload(AllotmentPending.to_user)
        ).filter(
            AllotmentPending.from_user_id == user_id,
            AllotmentPending.status == "pending"
        ).all()
        
        result = []
        for allotment in pending_allotments:
            # Get component type of first component for this pending allotment
            first_component = db.query(EVMComponent.component_type).join(
                AllotmentItemPending, 
                EVMComponent.id == AllotmentItemPending.evm_component_id
            ).filter(
                AllotmentItemPending.allotment_pending_id == allotment.id
            ).first()
            
            component_type = first_component.component_type if first_component else None
            
            result.append({
                "id": allotment.id,
                "allotment_type": allotment.allotment_type,
                "to_user_name": allotment.to_user.username if allotment.to_user else None,
                "from_local_body_id": allotment.from_local_body_id,
                "from_local_body_name": allotment.from_local_body.name if allotment.from_local_body else None,
                "to_local_body_id": allotment.to_local_body_id,
                "to_local_body_name": allotment.to_local_body.name if allotment.to_local_body else None,
                "from_district_name": allotment.from_district.name if allotment.from_district else None,
                "to_district_name": allotment.to_district.name if allotment.to_district else None,
                "component_type": component_type,  # Single component type
                "created_at": allotment.created_at,
            })
        
        return result
    
def view_pending_allotment_components(pending_allotment_id: int, user_id: int):
    with Database.get_session() as db:
        # Verify the pending allotment belongs to the user
        pending_allotment = db.query(AllotmentPending).filter(
            AllotmentPending.id == pending_allotment_id,
            AllotmentPending.from_user_id == user_id
        ).first()
        
        if not pending_allotment:
            raise HTTPException(status_code=404, detail="Pending allotment not found")
        
        # Get all components for this pending allotment
        components = db.query(EVMComponent).join(
            AllotmentItemPending, 
            EVMComponent.id == AllotmentItemPending.evm_component_id
        ).filter(
            AllotmentItemPending.allotment_pending_id == pending_allotment_id
        ).all()
        
        return [
            {
                "id": component.id,
                "serial_number": component.serial_number,
                "box_no": component.box_no,
                "dom": component.dom,
                "status": component.status,
                "warehouse": component.current_warehouse_id,
                "paired_components": [
                    {
                        "id": paired_component.id,
                        "component_type": paired_component.component_type,
                        "serial_number": paired_component.serial_number,
                    } 
                    for paired_component in (component.pairing.components if component.pairing else [])
                    if paired_component.id != component.id
                ]
            } for component in components
        ]

def remove_pending_allotment(pending_allotment_id: int, user_id: int):
    with Database.get_session() as db:
        # Fetch the pending allotment and verify ownership
        pending_allotment = db.query(AllotmentPending).filter(
            AllotmentPending.id == pending_allotment_id,
            AllotmentPending.from_user_id == user_id
        ).first()

        if not pending_allotment:
            raise HTTPException(status_code=404, detail="Pending allotment not found or unauthorized")

        # Fetch all item records
        items = db.query(AllotmentItemPending).filter(
            AllotmentItemPending.allotment_pending_id == pending_allotment_id
        ).all()

        # Optional: Reset component status
        for item in items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if component:
                # Restore status — adjust this logic as per your domain rule
                component.status = "FLC_Passed"

        # Delete items
        db.query(AllotmentItemPending).filter(
            AllotmentItemPending.allotment_pending_id == pending_allotment_id
        ).delete()

        # Delete the pending allotment itself
        db.delete(pending_allotment)
        db.commit()

        return {"status_code": 200, "message": "Pending allotment deleted successfully"}

def approve_allotment(allotment_id: int, approver_id: int):
    with Database.get_session() as db:
        allotment = db.query(Allotment).filter(Allotment.id == allotment_id).first()
        if not allotment:
            raise HTTPException(status_code=403, detail="Allotment not found.")
        if allotment.status == "approved":
            raise HTTPException(status_code=400, detail="Allotment already approved.")
        if allotment.status == "rejected":
            raise HTTPException(status_code=400, detail="Cannot approve a rejected allotment.")

        # Fetch approver user to get warehouse_id
        approver = db.query(User).filter(User.id == approver_id).first()


        allotment.status = "approved"
        allotment.approved_by_id = approver_id
        allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))

        updated_component_ids = []
        
        for item in allotment.items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if not component:
                continue

            # Always update the directly allotted component
            component.current_user_id = allotment.to_user_id
            component.current_warehouse_id = approver.warehouse_id
            updated_component_ids.append(component.id)
            component.status="FLC_Passed"

            # If the component is part of a pairing, update all in the pair
            if component.pairing_id:
                paired_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == component.pairing_id
                ).all()
                for paired in paired_components:
                    paired.current_user_id = allotment.to_user_id
                    paired.current_warehouse_id = approver.warehouse_id
                    if paired.id not in updated_component_ids:
                        updated_component_ids.append(paired.id)
        
        db.commit()
        db.refresh(allotment)

        # CREATE LOGS - Add corresponding entries to logs tables
        # 1. Create AllotmentLogs entry (approved state)
        allotment_log = AllotmentLogs(
            allotment_type=allotment.allotment_type,
            from_user_id=allotment.from_user_id,
            to_user_id=allotment.to_user_id,
            from_local_body_id=allotment.from_local_body_id,
            to_local_body_id=allotment.to_local_body_id,
            from_district_id=allotment.from_district_id,
            to_district_id=allotment.to_district_id,
            status=allotment.status,
            created_at=allotment.created_at,
            approved_at=allotment.approved_at
        )
        db.add(allotment_log)
        db.commit()
        db.refresh(allotment_log)

        # 2. Create EVMComponentLogs entries for all updated components
        component_log_ids = []
        for comp_id in updated_component_ids:
            component = db.query(EVMComponent).filter(EVMComponent.id == comp_id).first()
            
            comp_log = EVMComponentLogs(
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
            db.add(comp_log)
            db.commit()
            db.refresh(comp_log)
            component_log_ids.append(comp_log.id)

        # 3. Create AllotmentItemLogs entries (only for originally allotted items)
        for i, item in enumerate(allotment.items):
            # Find the corresponding component log
            original_component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            matching_log_id = None
            
            for j, comp_id in enumerate(updated_component_ids):
                if comp_id == item.evm_component_id:
                    matching_log_id = component_log_ids[j]
                    break
            
            if matching_log_id:
                db.add(AllotmentItemLogs(
                    allotment_id=allotment_log.id,
                    evm_component_id=matching_log_id,
                    remarks=item.remarks
                ))

        db.commit()

        return Response(status_code=200)

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
                        "component_type": item.evm_component.component_type,
                        "serial_number": item.evm_component.serial_number,
                        "paired_components": [
                            {
                                "component_type": paired_comp.component_type,
                                "serial_number": paired_comp.serial_number,
                                
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
    
def reject_allotment(allotment_id: int, reject_reason: str, approver_id: int):
    with Database.get_session() as db:
        allotment = db.query(Allotment).filter(Allotment.id == allotment_id).first()
        if not allotment:
            raise HTTPException(status_code=404, detail="Allotment not found.")
        if allotment.status == "approved":
            raise HTTPException(status_code=400, detail="Allotment already approved.")
        if allotment.status == "rejected":
            raise HTTPException(status_code=400, detail="Allotment already rejected.")

        approver = db.query(User).filter(User.id == approver_id).first()


        # Just mark as rejected — don't update component ownership
        allotment.status = "rejected"
        allotment.approved_by_id = approver_id
        allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))
        allotment.reject_reason = reject_reason
        db.commit()
        db.refresh(allotment)

        # CREATE LOGS - Add corresponding entries to logs tables
        # 1. Create AllotmentLogs entry (rejected state)
        allotment_log = AllotmentLogs(
            allotment_type=allotment.allotment_type,
            from_user_id=allotment.from_user_id,
            to_user_id=allotment.to_user_id,
            from_local_body_id=allotment.from_local_body_id,
            to_local_body_id=allotment.to_local_body_id,
            from_district_id=allotment.from_district_id,
            to_district_id=allotment.to_district_id,
            reject_reason=allotment.reject_reason,
            status=allotment.status,
            created_at=allotment.created_at,
            approved_at=allotment.approved_at
        )
        db.add(allotment_log)
        db.commit()
        db.refresh(allotment_log)

        # 2. Create EVMComponentLogs entries (components remain unchanged)
        for item in allotment.items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if component:
                component.status="FLC_Passed"
                comp_log = EVMComponentLogs(
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
                db.add(comp_log)
                db.commit()
                db.refresh(comp_log)

                # 3. Create AllotmentItemLogs entry
                db.add(AllotmentItemLogs(
                    allotment_id=allotment_log.id,
                    evm_component_id=comp_log.id,
                    remarks=item.remarks
                ))

        db.commit()
        return Response(status_code=200)


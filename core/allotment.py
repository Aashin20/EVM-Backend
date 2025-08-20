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
from core.create_allotment import AllotmentModel
from sqlalchemy.orm import aliased

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
        from sqlalchemy import func
        
        component_subquery = db.query(
            AllotmentItemPending.allotment_pending_id,
            func.min(EVMComponent.component_type).label('component_type')
        ).join(
            EVMComponent, EVMComponent.id == AllotmentItemPending.evm_component_id
        ).group_by(AllotmentItemPending.allotment_pending_id).subquery()
        
        pending_allotments = db.query(
            AllotmentPending,
            component_subquery.c.component_type
        ).options(
            joinedload(AllotmentPending.from_local_body),
            joinedload(AllotmentPending.to_local_body),
            joinedload(AllotmentPending.from_district),
            joinedload(AllotmentPending.to_district),
            joinedload(AllotmentPending.to_user)
        ).outerjoin(
            component_subquery, 
            AllotmentPending.id == component_subquery.c.allotment_pending_id
        ).filter(
            AllotmentPending.from_user_id == user_id,
            AllotmentPending.status == "pending"
        ).all()
        
        result = []
        for allotment, component_type in pending_allotments:
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
                "component_type": component_type,
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

   
        for item in items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if component:
              
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

        if allotment.is_temporary:
            allotment.status = "temporary_approved"
            allotment.approved_by_id = approver_id
            allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))
        else:
            allotment.status = "approved"
            allotment.approved_by_id = approver_id
            allotment.approved_at = datetime.now(ZoneInfo("Asia/Kolkata"))

        updated_component_ids = []

        # List of allotment types where warehouse should NOT be updated
        skip_warehouse_update_types = {
            AllotmentType.BO_TO_DEO,
            AllotmentType.CERO_TO_DEO,
            AllotmentType.MERO_TO_DEO,
            AllotmentType.ERO_TO_DEO,
        }

        for item in allotment.items:
            component = db.query(EVMComponent).filter(EVMComponent.id == item.evm_component_id).first()
            if not component:
                continue

            component.current_user_id = allotment.to_user_id

            if allotment.allotment_type not in skip_warehouse_update_types:
                component.current_warehouse_id = approver.warehouse_id

            updated_component_ids.append(component.id)

            if component.status == "FLC_Passed/Temp":
                component.status = "FLC_Passed"
            elif component.status == "FLC_Pending/Pending":
                component.status = "FLC_Pending"
            elif component.status == "FLC_Passed/Pending":
                component.status = "FLC_Passed"

            # Update all components in the pairing if any
            if component.pairing_id:
                paired_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == component.pairing_id
                ).all()
                for paired in paired_components:
                    paired.current_user_id = allotment.to_user_id
                    if allotment.allotment_type not in skip_warehouse_update_types:
                        paired.current_warehouse_id = approver.warehouse_id
                    if paired.id not in updated_component_ids:
                        updated_component_ids.append(paired.id)

        db.commit()
        db.refresh(allotment)

        # CREATE LOGS - Add corresponding entries to logs tables

        # 1. Allotment log
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

        # 2. Component logs
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

        # 3. Allotment item logs
        for i, item in enumerate(allotment.items):
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
                        "box_no": item.evm_component.box_no,
                        "paired_components": [
                            {
                                "component_type": paired_comp.component_type,
                                "serial_number": paired_comp.serial_number,
                                "box_no": paired_comp.box_no
                                
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
                if component.status=="FLC_Passed/Pending":
                    component.status="FLC_Passed"
                elif component.status=="FLC_Pending/Pending":
                    component.status="FLC_Pending"
            
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


def return_temporary_allotment(allotment_id: int, return_date: str, user_id: int):  #Return temporary allotment
    try:
        with Database.get_session() as db:
            # 1. Fetch the allotment
            allotment = db.query(Allotment).filter(Allotment.id == allotment_id).first()
            if not allotment:
                raise HTTPException(status_code=404, detail="Allotment not found.")
            if not allotment.is_temporary:
                raise HTTPException(status_code=400, detail="Allotment is not temporary.")

            # 2. Update return date and status
            allotment.temporary_return_date = return_date
            allotment.status = "returned"
            db.add(allotment)

            # 3. Log allotment return
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
            )
            db.add(allotment_log)

            # 4. Fetch all related EVM components in a single query
            component_ids = [item.evm_component_id for item in allotment.items]
            components = db.query(EVMComponent).filter(EVMComponent.id.in_(component_ids)).all()

            for component in components:
                # Set status back to FLC_Pendings
                component.status = "FLC_Pending"
                
                # Logging
                comp_log = EVMComponentLogs(
                    serial_number=component.serial_number,
                    component_type=component.component_type,
                    status=component.status,
                    is_verified=component.is_verified,
                    dom=component.dom,
                    box_no=component.box_no,
                    current_user_id=component.current_user_id,
                    current_warehouse_id=component.current_warehouse_id,
                    pairing_id=component.pairing_id,
                )
                db.add(comp_log)

            db.commit()
            db.refresh(allotment)
            db.refresh(allotment_log)

    except Exception as e:
        # Optional: Add more detailed logging
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

def view_temporary(user_id: int):
    with Database.get_session() as db:
        temporary_allotments = db.query(Allotment).options(
            joinedload(Allotment.items)
            .joinedload(AllotmentItem.evm_component)
            .joinedload(EVMComponent.pairing)
            .joinedload(PairingRecord.components)
        ).filter(
            Allotment.from_user_id == user_id,
            Allotment.is_temporary == True,
        ).all()

        if not temporary_allotments:
            return {"message": "No temporary allotments found."}

        seal_types = {
            EVMComponentType.DMM_SEAL,
            EVMComponentType.PINK_PAPER_SEAL,
            EVMComponentType.BU_PINK_PAPER_SEAL
        }

        result = []

        for allotment in temporary_allotments:
            components_list = []
            added_ids = set()

            for item in allotment.items:
                component = item.evm_component

                if component.component_type in seal_types:
                    continue

                if component.id not in added_ids:
                    components_list.append({
                        "serial_number": component.serial_number,
                        "component_type": component.component_type
                    })
                    added_ids.add(component.id)

                if component.component_type == EVMComponentType.CU and component.pairing:
                    for paired in component.pairing.components:
                        if paired.id not in added_ids and paired.component_type not in seal_types:
                            components_list.append({
                                "serial_number": paired.serial_number,
                                "component_type": paired.component_type
                            })
                            added_ids.add(paired.id)

            result.append({
                "id": allotment.id,
                "allotment_type": allotment.allotment_type,
                "from_user_id": allotment.from_user_id,
                "components": components_list,
                "created_at": allotment.created_at.strftime("%Y-%m-%d"),
                "temporary_allotted_to_name": allotment.temporary_allotted_to_name,
                "temporary_reason": allotment.temporary_reason,
                "temporary_return_date": allotment.temporary_return_date,
            })

        return result



def view_all_allotments_deo(district_id: str): # For DEO: View all allotments in districts 
    with Database.get_session() as db: 
        from_lb = aliased(LocalBody) 
        to_lb = aliased(LocalBody) 
         
        allotments = db.query(Allotment).outerjoin( 
            from_lb, Allotment.from_local_body_id == from_lb.id 
        ).outerjoin( 
            to_lb, Allotment.to_local_body_id == to_lb.id 
        ).filter( 
            (Allotment.from_district_id == district_id) | 
            (Allotment.to_district_id == district_id) | 
            (from_lb.district_id == district_id) | 
            (to_lb.district_id == district_id) 
        ).options( 
            joinedload(Allotment.from_local_body), 
            joinedload(Allotment.to_local_body),
            joinedload(Allotment.from_user),
            joinedload(Allotment.to_user)
        ).all() 
         
        return [{ 
            "id": a.id, 
            "from_user": a.from_user.username if a.from_user else None,
            "to_user": a.to_user.username if a.to_user else None,
            "from_local_body": a.from_local_body.name if a.from_local_body else None, 
            "to_local_body": a.to_local_body.name if a.to_local_body else None, 
            "status": a.status, 
            "created_at": a.created_at.isoformat(), 
        } for a in allotments] 
 
 
     
def view_all_allotments_sec():  # For SEC: View all allotments across all districts 
    with Database.get_session() as db: 
        allotments = db.query(Allotment).options( 
            joinedload(Allotment.from_local_body).joinedload(LocalBody.district), 
            joinedload(Allotment.to_local_body).joinedload(LocalBody.district),
            joinedload(Allotment.from_user),
            joinedload(Allotment.to_user)
        ).all() 
 
        result = [] 
        for a in allotments: 
            result.append({ 
                "id": a.id, 
                "from_user": a.from_user.username if a.from_user else None,
                "to_user": a.to_user.username if a.to_user else None,
                "from_local_body": a.from_local_body.name if a.from_local_body else None, 
                "from_district": a.from_local_body.district.name if a.from_local_body and a.from_local_body.district else None, 
                "to_local_body": a.to_local_body.name if a.to_local_body else None, 
                "to_district": a.to_local_body.district.name if a.to_local_body and a.to_local_body.district else None, 
                "status": a.status, 
                "created_at": a.created_at.isoformat(), 
            }) 
        return result
    
def view_allotment_items(allotment_id: int):
    with Database.get_session() as db:
        allotment_exists = db.query(AllotmentLogs.id).filter(AllotmentLogs.id == allotment_id).first()
        if not allotment_exists:
            raise HTTPException(status_code=404, detail="Allotment not found.")

  
        allowed_types = (EVMComponentType.CU, EVMComponentType.BU, EVMComponentType.DMM)


        items = (
            db.query(EVMComponentLogs.serial_number, EVMComponentLogs.component_type)
            .join(AllotmentItemLogs, AllotmentItemLogs.evm_component_id == EVMComponentLogs.id)
            .filter(
                AllotmentItemLogs.allotment_id == allotment_id,
                EVMComponentLogs.component_type.in_(allowed_types)
            )
            .all()
        )


        return [
            {"serial_number": serial, "component_type": ctype}
            for serial, ctype in items
        ]
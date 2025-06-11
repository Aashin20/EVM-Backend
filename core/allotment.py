from models.evm import AllotmentItem, FLCRecord, FLCBallotUnit,Allotment,EVMComponent
from models.logs import AllotmentLogs,EVMComponentLogs,AllotmentItemLogs, PairingRecordLogs
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
    reject_reason: Optional[str] = None


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



def create_allotment(evm: AllotmentModel, from_user_id: int):  
    with Database.get_session() as db:
        components = db.query(EVMComponent).filter(
            EVMComponent.id.in_(evm.evm_component_ids)
        ).all()



        for comp in components:
            if comp.status in ["Polled", "Counted","FLC_Failed", "Faulty"]:
                raise HTTPException(status_code=400, detail=f"Component {comp.serial_number} is not available.")
            if comp.current_user_id != from_user_id:
                raise HTTPException(status_code=403, detail=f"Component {comp.serial_number} is not owned by the sender.")

        # Create the main allotment
        allotment = Allotment(
            allotment_type=evm.allotment_type,
            from_user_id=from_user_id,
            to_user_id=evm.to_user_id,
            from_local_body_id=evm.from_local_body_id,
            to_local_body_id=evm.to_local_body_id,
            from_district_id=evm.from_district_id,
            to_district_id=evm.to_district_id,
            original_allotment_id=evm.original_allotment_id,
            initiated_by_id=from_user_id,
            status="pending"
        )
        db.add(allotment)
        db.commit()
        db.refresh(allotment)

        # Create allotment items
        for comp in components:
            comp.status="FLC_Passed/Temp"
            db.add(AllotmentItem(allotment_id=allotment.id, evm_component_id=comp.id))

        db.commit()

        # CREATE LOGS - Add this section
        # 1. Create AllotmentLogs entry
        allotment_log = AllotmentLogs(
            allotment_type=allotment.allotment_type,
            from_user_id=allotment.from_user_id,
            to_user_id=allotment.to_user_id,
            from_local_body_id=allotment.from_local_body_id,
            to_local_body_id=allotment.to_local_body_id,
            from_district_id=allotment.from_district_id,
            to_district_id=allotment.to_district_id,
            status=allotment.status,
            created_at=allotment.created_at  # or let it default to current time
        )
        db.add(allotment_log)
        db.commit()
        db.refresh(allotment_log)

        # 2. Create EVMComponentLogs entries for each component
        component_log_ids = []
        for comp in components:
            comp_log = EVMComponentLogs(
                serial_number=comp.serial_number,
                component_type=comp.component_type,
                status=comp.status,
                is_verified=comp.is_verified,
                dom=comp.dom,
                box_no=comp.box_no,
                current_user_id=comp.current_user_id,
                current_warehouse_id=comp.current_warehouse_id,
                pairing_id=comp.pairing_id
            )
            db.add(comp_log)
            db.commit()
            db.refresh(comp_log)
            component_log_ids.append(comp_log.id)

        # 3. Create AllotmentItemLogs entries
        for i, comp in enumerate(components):
            db.add(AllotmentItemLogs(
                allotment_id=allotment_log.id,
                evm_component_id=component_log_ids[i]
            ))

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


def evm_commissioning(commissioning_list: List[EVMCommissioningModel], user_id: int):
    with Database.get_session() as db:
        validation_errors = []
        
        try:
            for idx, commissioning_data in enumerate(commissioning_list):
                # Convert ps_no to integer if it's a string
                try:
                    ps_no = int(commissioning_data.ps_no)
                except ValueError:
                    validation_errors.append(f"Row {idx+1}: Invalid polling station number: {commissioning_data.ps_no}")
                    continue
                
                # 1. Validate CU
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                
                if not cu:
                    validation_errors.append(f"Row {idx+1}: CU {commissioning_data.cu_serial} not found")
                    continue
                
                if not cu.pairing_id:
                    validation_errors.append(f"Row {idx+1}: CU {commissioning_data.cu_serial} does not have a pairing record")
                    continue
                
                # 2. Validate pairing
                pairing = db.query(PairingRecord).filter(
                    PairingRecord.id == cu.pairing_id
                ).first()
                
                if not pairing:
                    validation_errors.append(f"Row {idx+1}: Pairing record not found")
                    continue
                
                if pairing.polling_station_id:
                    validation_errors.append(f"Row {idx+1}: Already assigned to polling station")
                    continue
                
                if pairing.evm_id:
                    validation_errors.append(f"Row {idx+1}: Already has EVM number")
                    continue
                
                # 3. Validate polling station
                polling_station = db.query(PollingStation).filter(
                    PollingStation.id == ps_no
                ).first()
                
                if not polling_station:
                    validation_errors.append(f"Row {idx+1}: Polling station {ps_no} not found")
                    continue
                
                # 4. Validate all BUs
                for bu_serial in commissioning_data.bu_serial:
                    bu = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == bu_serial,
                        EVMComponent.component_type == EVMComponentType.BU
                    ).first()
                    
                    if not bu:
                        validation_errors.append(f"Row {idx+1}: BU {bu_serial} not found")
                    elif bu.pairing_id and bu.pairing_id != cu.pairing_id:
                        validation_errors.append(f"Row {idx+1}: BU {bu_serial} already assigned elsewhere")
        
        except Exception as e:
            print(f"Validation error: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error during validation: {str(e)}"
            )
        
        # If ANY validation errors, reject entire batch
        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Validation failed. No EVMs were commissioned.",
                    "errors": validation_errors
                }
            )
        
        # All validations passed - now apply all changes
        try:
            for commissioning_data in commissioning_list:
                # Convert ps_no to integer
                ps_no = int(commissioning_data.ps_no)
                
                # Get CU and pairing (we know they exist from validation)
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                
                pairing = db.query(PairingRecord).filter(
                    PairingRecord.id == cu.pairing_id
                ).first()
                
                # Update pairing
                pairing.evm_id = commissioning_data.evm_no
                pairing.polling_station_id = ps_no
                pairing.completed_by_id = user_id
                pairing.completed_at = datetime.now(ZoneInfo("Asia/Kolkata"))
                
                # Update CU status
                cu.status = "polling"
                
                # Assign BUs to pairing and update their status
                for bu_serial in commissioning_data.bu_serial:
                    bu = db.query(EVMComponent).filter(
                        EVMComponent.serial_number == bu_serial,
                        EVMComponent.component_type == EVMComponentType.BU
                    ).first()
                    bu.pairing_id = cu.pairing_id
                    bu.status = "polling"
                
                # Update status for all other components in this pairing
                other_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == cu.pairing_id,
                    EVMComponent.component_type.in_([
                        EVMComponentType.DMM,
                        EVMComponentType.DMM_SEAL,
                        EVMComponentType.PINK_PAPER_SEAL
                    ])
                ).all()
                
                for component in other_components:
                    component.status = "polling"
            
            db.commit()
            
            # CREATE LOGS - Add corresponding entries to logs tables
            for commissioning_data in commissioning_list:
                ps_no = int(commissioning_data.ps_no)
                
                # Get updated pairing
                cu = db.query(EVMComponent).filter(
                    EVMComponent.serial_number == commissioning_data.cu_serial,
                    EVMComponent.component_type == EVMComponentType.CU
                ).first()
                
                pairing = db.query(PairingRecord).filter(
                    PairingRecord.id == cu.pairing_id
                ).first()
                
                # 1. Create PairingRecordLogs entry
                pairing_log = PairingRecordLogs(
                    evm_id=pairing.evm_id,
                    polling_station_id=pairing.polling_station_id,
                    created_by_id=pairing.created_by_id,
                    created_at=pairing.created_at,
                    completed_by_id=pairing.completed_by_id,
                    completed_at=pairing.completed_at
                )
                db.add(pairing_log)
                db.commit()
                db.refresh(pairing_log)
                
                # 2. Create EVMComponentLogs entries for all components in this pairing
                all_components = db.query(EVMComponent).filter(
                    EVMComponent.pairing_id == cu.pairing_id
                ).all()
                
                for component in all_components:
                    comp_log = EVMComponentLogs(
                        serial_number=component.serial_number,
                        component_type=component.component_type,
                        status=component.status,
                        is_verified=component.is_verified,
                        dom=component.dom,
                        box_no=component.box_no,
                        current_user_id=component.current_user_id,
                        current_warehouse_id=component.current_warehouse_id,
                        pairing_id=pairing_log.id
                    )
                    db.add(comp_log)
                
            db.commit()
            
            return Response(status_code=200)
        except Exception as e:
            db.rollback()
            print(f"Commission error: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Database error during commission: {str(e)}"
            )
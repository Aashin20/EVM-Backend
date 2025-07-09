from fastapi import APIRouter, Depends, HTTPException,Body,Query,Request
from core.allotment import (reject_allotment,approve_allotment, 
                            approval_queue,view_pending_allotment_components,
                            view_pending_allotments,pending,remove_pending_allotment,
                            view_temporary,return_temporary_allotment)
from core.commissioning import evm_commissioning,EVMCommissioningModel,view_reserve,allot_reserve_evm_to_polling_station,ReserveEVMCommissioningModel
from core.create_allotment import create_allotment, AllotmentModel
from utils.authtoken import get_current_user
from typing import List,Optional

router = APIRouter()

@router.post("/")
async def allot_evm(data: AllotmentModel,pending_id: Optional[int] = Query(None),current_user: dict = Depends(get_current_user)):
    return create_allotment(data,current_user['user_id'],pending_id)

@router.get("/pending/view")
async def pending_view(current_user: dict = Depends(get_current_user)):
    return view_pending_allotments(current_user['user_id'])

@router.post("/pending")
async def pending_create(data: AllotmentModel,current_user: dict = Depends(get_current_user)):
    return pending(data,current_user['user_id'])

@router.get("/pending/components/{pending_id}")
async def view_pending_comp(pending_id:int,current_user: dict = Depends(get_current_user)):
    return view_pending_allotment_components(pending_id,current_user['user_id'])

@router.get("/pending/remove/{pending_id}")
async def remove_pending(pending_id:int,current_user: dict = Depends(get_current_user)):
    return remove_pending_allotment(pending_id,current_user['user_id'])

@router.get("/approve/{allotment_id}")
async def approve(allotment_id: int,current_user: dict = Depends(get_current_user)):  
    return approve_allotment(allotment_id,current_user['user_id'])

@router.get("/reject/{allotment_id}/{reject_reason}")
async def reject(allotment_id: int,reject_reason:str,current_user: dict = Depends(get_current_user)):  
    return reject_allotment(allotment_id,reject_reason,current_user['user_id'])

@router.get("/queue/")
async def queue(current_user: dict = Depends(get_current_user)):
    return approval_queue(current_user['user_id'])

@router.post("/commission")
async def evm_commissioning_route(data: List[EVMCommissioningModel] = Body(...),current_user: dict = Depends(get_current_user)):
    return evm_commissioning(data, current_user['user_id'])
    
@router.get("/reserve")
async def reserve_view(current_user: dict = Depends(get_current_user)):
    return view_reserve(current_user['user_id'])

@router.post("/reserve/allot")
async def allot_reserve_evm(data:ReserveEVMCommissioningModel,psno:int,current_user:dict = Depends(get_current_user)):
    return allot_reserve_evm_to_polling_station(data,psno,current_user['user_id'])

@router.get("/temporary")
async def view_temporary_allotments(current_user: dict = Depends(get_current_user)):
    return view_temporary(current_user['user_id'])

@router.post("/temporary/return/")
async def return_temporary(allotment_id: int, return_date: str, current_user: dict = Depends(get_current_user)):
    if not allotment_id or not return_date:
        raise HTTPException(status_code=400, detail="Allotment ID and return date are required")
    return return_temporary_allotment(allotment_id, return_date, current_user['user_id'])
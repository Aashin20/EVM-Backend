from fastapi import APIRouter, Depends, HTTPException,Body,Query
from core.allotment import (create_allotment, AllotmentModel, reject_allotment,approve_allotment, 
                            approval_queue, evm_commissioning,EVMCommissioningModel,
                            view_pending_allotment_components,view_pending_allotments,pending)
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
    
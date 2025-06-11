from fastapi import APIRouter, Depends, HTTPException,Body
from core.allotment import create_allotment, AllotmentModel, reject_allotment,approve_allotment, approval_queue, evm_commissioning,EVMCommissioningModel
from utils.authtoken import get_current_user
from typing import List


router = APIRouter()

@router.post("/")
async def allot_evm(data: AllotmentModel,current_user: dict = Depends(get_current_user)):
    return create_allotment(data,current_user['user_id'])

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
    
from fastapi import APIRouter, Depends, HTTPException
from core.allotment import create_allotment, AllotmentModel, reject_allotment,approve_allotment, approval_queue
from utils.authtoken import get_current_user
from typing import List

router = APIRouter()

@router.post("/")
async def allot_evm(data: AllotmentModel,current_user: dict = Depends(get_current_user)):
    return create_allotment(data)

@router.get("/approve/{allotment_id}")
async def approve(allotment_id: int,current_user: dict = Depends(get_current_user)):  
    return approve_allotment(allotment_id,current_user['user_id'])

@router.get("/reject/{allotment_id}")
async def reject(allotment_id: int,current_user: dict = Depends(get_current_user)):  
    return reject_allotment(allotment_id,current_user['user_id'])

@router.get("/queue/")
async def queue(current_user: dict = Depends(get_current_user)):
    return approval_queue(current_user['user_id'])
    
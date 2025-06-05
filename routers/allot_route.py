from fastapi import APIRouter, Depends, HTTPException
from core.allotment import create_allotment, AllotmentModel, AllotmentResponse,approve_allotment
from utils.authtoken import get_current_user

router = APIRouter()

@router.post("/", response_model=AllotmentResponse)
async def allot_evm(data: AllotmentModel,current_user: dict = Depends(get_current_user)):
    return create_allotment(data)

@router.post("/approve/{allotment_id}")
async def approve(allotment_id: int,current_user: dict = Depends(get_current_user)):  
    return approve_allotment(allotment_id,current_user['id'])
    
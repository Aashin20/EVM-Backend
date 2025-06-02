from fastapi import APIRouter
from core.allotment import create_allotment, AllotmentModel, AllotmentResponse,approve_allotment

router = APIRouter()

@router.post("/", response_model=AllotmentResponse)
async def allot_evm(data: AllotmentModel):
    return create_allotment(data)

@router.post("/approve/{allotment_id}")
async def approve(allotment_id: int,current_user_id: int=1):  #Replace using depends
    return approve_allotment(allotment_id,current_user_id)
    
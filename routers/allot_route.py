from fastapi import APIRouter
from core.allotment import create_allotment, AllotmentModel, AllotmentResponse,approve_allotment

router = APIRouter()

@router.post("/", response_model=AllotmentResponse)
async def allot_evm(data: AllotmentModel):
    return create_allotment(data)


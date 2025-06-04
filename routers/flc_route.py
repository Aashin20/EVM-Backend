from fastapi import APIRouter
from core.flc import flc_cu, FLCCUModel, FLCBUModel, flc_bu
from typing import List

router = APIRouter()

@router.post("/cu")
async def flc_cu_bulk(data: List[FLCCUModel]):
    return flc_cu(data)

from fastapi import APIRouter, Depends
from core.flc import flc_cu, FLCCUModel, FLCBUModel, flc_bu
from typing import List
from utils.authtoken import get_current_user
from fastapi import HTTPException

router = APIRouter()

@router.post("/cu")
async def flc_cu_bulk(data: List[FLCCUModel], current_user: dict = Depends(get_current_user)):
    print(f"Current user role: {current_user['role']}", flush=True)
    if current_user['role'] not in ['Developer', 'FLC Officer']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    else:
        return flc_cu(data,current_user['user_id'])

@router.post("/bu")
async def flc_bu_bulk(data: List[FLCBUModel],current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'FLC Officer']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return flc_bu(data)
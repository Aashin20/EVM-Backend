from fastapi import APIRouter, Depends
from core.flc import flc_cu, FLCCUModel, FLCBUModel,FLCDMMModel, flc_bu,flc_dmm
from typing import List
from utils.authtoken import get_current_user
from fastapi import HTTPException,BackgroundTasks

router = APIRouter()

@router.post("/cu")
async def flc_cu_bulk(data: List[FLCCUModel],background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
        return flc_cu(data,current_user['user_id'],background_tasks)

@router.post("/bu")
async def flc_bu_bulk(data: List[FLCBUModel],background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'FLC Officer']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return flc_bu(data,current_user['user_id'],background_tasks)

@router.post("/dmm")
async def flc_dmm_bulk(data: List[FLCDMMModel],background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'FLC Officer']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return flc_dmm(data,current_user['user_id'],background_tasks)
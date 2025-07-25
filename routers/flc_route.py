from fastapi import APIRouter, Depends, Request  
from core.flc import flc_cu, FLCCUModel, FLCBUModel, FLCDMMModel, flc_bu, flc_dmm,view_flc_components,view_all_districts_flc_summary
from typing import List
from utils.authtoken import get_current_user
from fastapi import HTTPException, BackgroundTasks
from utils.rate_limiter import limiter

router = APIRouter()

@router.post("/cu")
@limiter.limit("30/minute")
async def flc_cu_bulk(request: Request, data: List[FLCCUModel], background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)): # Added Request parameter
        return flc_cu(data, current_user['user_id'], background_tasks)

@router.post("/bu")
@limiter.limit("30/minute")
async def flc_bu_bulk(request: Request, data: List[FLCBUModel], background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)): # Added Request parameter
    if current_user['role'] not in ['Developer', 'FLC Officer']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return flc_bu(data, current_user['user_id'], background_tasks)

@router.post("/dmm")
@limiter.limit("30/minute")
async def flc_dmm_bulk(request: Request, data: List[FLCDMMModel], background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)): # Added Request parameter
    if current_user['role'] not in ['Developer', 'FLC Officer']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return flc_dmm(data, current_user['user_id'], background_tasks)
    
@router.get('/view/{component_type}/{district_id}')
@limiter.limit("30/minute")
async def view_flc_components_route(request: Request,component_type: str, district_id: str,current_user: dict = Depends(get_current_user)):
     return view_flc_components(component_type, district_id)

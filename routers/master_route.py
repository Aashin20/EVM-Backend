from fastapi import APIRouter,Query,Path,Request
from core.user import (register, RegisterModel, view_users,UpdateUserModel,
                       edit_user,add_ps,approve_ps,reject_ps,view_ps,
                       PollingStationModel,get_ps,mass_deactivate,
                       add_warehouse)
from core.allotment import view_all_allotments_deo,view_all_allotments_sec
from utils.authtoken import get_current_user
from fastapi import Depends
from typing import List,Optional
from core.components import dashboard_all,sec_dashboard
from pydantic import BaseModel
from utils.rate_limiter import limiter

class WarehouseCreate(BaseModel):
    district_id: int
    warehouse_name: str

router = APIRouter()

@router.post("/user/create")
async def register_user(details: RegisterModel,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC', 'DEO']:    
        return {"status" : 401, "message": "Unauthorized access"}
    else:
        return register(details)

@router.get("/user/view") #SEC ONLY
@limiter.limit("30/minute")
async def view(request: Request,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return view_users()

@router.post("/user/edit")
@limiter.limit("30/minute")
async def edit(request: Request,details: UpdateUserModel,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return edit_user(details)

@router.post("/ps/add")
@limiter.limit("30/minute")
async def add_ps_endpoint(request: Request,data: List[PollingStationModel],current_user: dict = Depends(get_current_user)):
    return add_ps(data)

@router.get("/ps/pending/{district_id}")
@limiter.limit("30/minute")
async def ps_view(request: Request,district_id: int,current_user: dict = Depends(get_current_user)):
    return view_ps(district_id)

@router.post("/ps/approve")
@limiter.limit("30/minute")
async def ps_approve(request: Request,ps_ids: List[int],current_user: dict = Depends(get_current_user)):
    return approve_ps(ps_ids, current_user['user_id'])

@router.post("/ps/reject")
@limiter.limit("30/minute")
async def ps_reject(request: Request,ps_ids: List[int], current_user: dict = Depends(get_current_user)):
    return reject_ps(ps_ids, current_user['user_id'])

@router.get("/ps/view/{local_body_id}")
@limiter.limit("30/minute")
async def view(request: Request,local_body_id:str,current_user: dict = Depends(get_current_user)):
    return get_ps(local_body_id)

@router.get("/dashboard")
@limiter.limit("30/minute")
async def dash(request: Request,current_user: dict = Depends(get_current_user)):
        return dashboard_all(current_user['user_id'])

@router.get("/dashboard/sec")
@limiter.limit("30/minute")
async def sec_dash(request: Request,current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'SEC':
        return {"status": 401, "message": "Unauthorized access"}
    return sec_dashboard()

@router.get("/toggle/{role}")
@limiter.limit("30/minute")
async def deactivate(request: Request,role:str,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    return mass_deactivate(role,current_user['user_id'])

@router.get("/dashboard/allotments/{district_id}")
@limiter.limit("30/minute")
async def view_allotments(request: Request,district_id:str =Path(...)):
    try:
        district_id=int(district_id)
        return view_all_allotments_deo(district_id)
    except (ValueError, TypeError):
        return view_all_allotments_sec()

@router.post("/warehouse/add")
@limiter.limit("30/minute")
async def warehouse_add(request: Request,data: WarehouseCreate):
    return add_warehouse(data.district_id,data.warehouse_name)
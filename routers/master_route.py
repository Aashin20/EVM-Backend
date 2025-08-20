from fastapi import APIRouter, Query, Path, Request
from core.user import (register, RegisterModel, view_users, UpdateUserModel,
                       edit_user, add_ps, approve_ps, reject_ps, view_ps,
                       PollingStationModel, get_ps, mass_deactivate,
                       add_warehouse)
from core.allotment import view_all_allotments_deo, view_all_allotments_sec
from utils.authtoken import get_current_user
from fastapi import Depends
from typing import List, Optional
from core.components import dashboard_all, sec_dashboard, FLC_dashboard
from pydantic import BaseModel
from utils.rate_limiter import limiter
from utils.redis import RedisClient
from utils.cache_decorator import cache_response

class WarehouseCreate(BaseModel):
    district_id: int
    warehouse_name: str

router = APIRouter()

@router.post("/user/create")
@limiter.limit("30/minute")
async def register_user(request: Request, details: RegisterModel, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC', 'DEO']:    
        return {"status" : 401, "message": "Unauthorized access"}
    else:
        await RedisClient.delete_pattern("user*") 
        return register(details)

@router.get("/users")
@cache_response(expire=3600, key_prefix="user_list", include_user=False)
@limiter.limit("30/minute")
async def view(
    request: Request,
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)"),
    username: Optional[str] = Query(None, description="Filter by username (partial match)"),
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    role: Optional[str] = Query(None, description="Filter by role name (partial match)"),
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return view_users(page,limit,username,district_id,role)

@router.post("/user/edit")
@limiter.limit("30/minute")
async def edit(request: Request, details: UpdateUserModel, current_user: dict = Depends(get_current_user)):
        await RedisClient.delete_pattern("user*") 
        return edit_user(details)

@router.post("/ps/add")
@limiter.limit("30/minute")
async def add_ps_endpoint(request: Request, data: List[PollingStationModel], current_user: dict = Depends(get_current_user)):
    await RedisClient.delete_pattern("ps*") 
    return add_ps(data)

@router.get("/ps/pending/{district_id}")
@limiter.limit("30/minute")
async def ps_view(request: Request, district_id: int, current_user: dict = Depends(get_current_user)):
    await RedisClient.delete_pattern("ps*") 
    return view_ps(district_id)

@router.post("/ps/approve")
@limiter.limit("30/minute")
async def ps_approve(request: Request, ps_ids: List[int], current_user: dict = Depends(get_current_user)):
    await RedisClient.delete_pattern("ps*") 
    return approve_ps(ps_ids, current_user['user_id'])

@router.post("/ps/reject")
@limiter.limit("30/minute")
async def ps_reject(request: Request, ps_ids: List[int], current_user: dict = Depends(get_current_user)):
    await RedisClient.delete_pattern("ps*") 
    return reject_ps(ps_ids, current_user['user_id'])

@router.get("/ps/view/{local_body_id}")
@cache_response(expire=3600, key_prefix="ps_view", include_user=False)
@limiter.limit("30/minute")
async def view_ps_data(request: Request, local_body_id: str, current_user: dict = Depends(get_current_user)):
    return get_ps(local_body_id)

@router.get("/dashboard")
@cache_response(expire=3600, key_prefix="comp_dashboard", include_user=True)
@limiter.limit("30/minute")
async def dash(request: Request,current_user: dict = Depends(get_current_user)):
    return dashboard_all(current_user['user_id'])

@router.get("/dashboard/sec")
@cache_response(expire=3600, key_prefix="comp_dashboard", include_user=True)
@limiter.limit("30/minute")
async def sec_dash(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'SEC':
        return {"status": 401, "message": "Unauthorized access"}
    return sec_dashboard()

@router.get("/dashboard/flc/{district_id}")
@cache_response(expire=3600, key_prefix="comp_flc_dashboard", include_user=False)
async def dashboard_flc(request: Request, district_id: str = Path(...),current_user: dict = Depends(get_current_user)):
    return FLC_dashboard(district_id)

@router.get("/toggle/{role}")
@limiter.limit("30/minute")
async def deactivate(request: Request, role: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    return mass_deactivate(role, current_user['user_id'])

@router.get("/dashboard/allotments/{district_id}")
@cache_response(expire=3600, key_prefix="allot_dashboard", include_user=False)
@limiter.limit("30/minute")
async def view_allotments(request: Request, district_id: str = Path(...),current_user: dict = Depends(get_current_user)):
    try:
        district_id = int(district_id)
        return view_all_allotments_deo(district_id)
    except (ValueError, TypeError):
        return view_all_allotments_sec()

@router.post("/warehouse/add")
@limiter.limit("30/minute")
async def warehouse_add(request: Request, data: WarehouseCreate,current_user: dict = Depends(get_current_user)):
    await RedisClient.delete_pattern("meta_warehouse*") 
    return add_warehouse(data.district_id, data.warehouse_name)

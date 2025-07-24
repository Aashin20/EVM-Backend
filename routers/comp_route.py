from fastapi import APIRouter, Depends, HTTPException, Path, Request
from core.components import (new_components, ComponentModel, view_paired_cu, view_components, 
                             view_paired_bu, view_paired_cu_sec,
                             view_paired_cu_deo, view_components_sec, view_components_deo,
                             view_paired_bu_deo, view_paired_bu_sec, approve_component_by_sec, approval_queue_sec,
                             view_dmm, warehouse_reentry, components_without_warehouse,warehouse_box_entry)
from typing import List, Dict, Any
from pydantic import BaseModel
from utils.authtoken import get_current_user
from core.return_ import damaged, view_damaged
from core.msr import (MSR_CU_DMM, MSR_BU, MSR_BU_user, MSR_CU_DMM_user,
                      MSR_BU_warehouse, MSR_CU_DMM_warehouse)
from utils.rate_limiter import limiter

class PairedCU(BaseModel):
    user_id : int

class PairedBU(BaseModel):
    user_id : int

router = APIRouter()

@router.post("/new")
@limiter.limit("30/minute")
async def create_new_components(request: Request, components: List[ComponentModel], order_no: str, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC','DEO', 'FLC Officer']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    else:
        return new_components(components, order_no,current_user['user_id'])

@router.get("/msr/unpaired/{component_type}/{district_id}")
@limiter.limit("30/minute")
async def cu(request: Request, component_type: str, district_id: str = Path(...), current_user: dict = Depends(get_current_user)):
    try:
        district_id=int(district_id)
        if current_user['role']=='DEO':
            return view_components_deo(component_type,district_id)
    except (ValueError, TypeError):
        return view_components_sec(component_type)
    
@router.get('/view/unpaired/{component_type}')
@limiter.limit("30/minute")
async def view_unpaired(request: Request, component_type: str, current_user: dict = Depends(get_current_user)):
    return view_components(component_type.upper(),current_user['user_id'])

@router.get("/msr/paired/cu/{district_id}")
@limiter.limit("30/minute")
async def paired_cu(request: Request, district_id: str = Path(...), current_user: dict = Depends(get_current_user)):
    try:
        district_id = int(district_id)
        if current_user['role'] == 'DEO':
            return view_paired_cu_deo(district_id)
    except (ValueError, TypeError):
        return view_paired_cu_sec()
    
@router.get("/view/paired/cu")
@limiter.limit("30/minute")
async def get_paired_cu(request: Request, current_user: dict = Depends(get_current_user)):
    return view_paired_cu(current_user['user_id'])

@router.get("/msr/paired/bu/{district_id}")
@limiter.limit("30/minute")
async def paired_bu(request: Request, district_id: str = Path(...), current_user: dict = Depends(get_current_user)):
    try:
        district_id = int(district_id)
        if current_user['role'] == 'DEO':
            return view_paired_bu_deo(district_id)
    except (ValueError, TypeError):
        return view_paired_bu_sec()
    
@router.get("/view/paired/bu")
@limiter.limit("30/minute")
async def get_paired_bu(request: Request, current_user: dict = Depends(get_current_user)):
    return view_paired_bu(current_user['user_id'])
      
@router.post("/approve")
@limiter.limit("30/minute")
async def approve_component(request: Request, serial_numbers: List[str], current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'SEC':
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return approve_component_by_sec(serial_numbers)

@router.get("/pending")
@limiter.limit("30/minute")
async def pending_approval(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'SEC':
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return approval_queue_sec()

@router.post("/damaged/add")
@limiter.limit("30/minute")
async def add_damaged(request: Request, evm_id: str, current_user: dict = Depends(get_current_user)):
    return damaged(evm_id)

@router.get("/damaged/view/{district_id}")
@limiter.limit("30/minute")
async def damaged_view(request: Request, district_id: int, current_user: dict = Depends(get_current_user)):
    return view_damaged(district_id)

@router.get("/reserve/dmm")
@limiter.limit("30/minute")
async def view_reserve_dmm(request: Request, current_user: dict = Depends(get_current_user)):
    return view_dmm(current_user['user_id'])

@router.get("/msr/details/cu")
@limiter.limit("30/minute")
async def get_msr_details_cu(request: Request):
    return MSR_CU_DMM()

@router.get("/msr/details/bu")
@limiter.limit("30/minute")
async def get_msr_details_bu(request: Request):
    return MSR_BU()

@router.get("/msr/details/bu/user/")
@limiter.limit("30/minute")
async def get_msr_details_bu_by_user(request: Request, current_user: dict = Depends(get_current_user)):
    return MSR_BU_user(current_user['user_id'])

@router.get("/msr/details/cu/user")
@limiter.limit("30/minute")
async def get_msr_details_cu_by_user(request: Request, current_user: dict = Depends(get_current_user)):
    return MSR_CU_DMM_user(current_user['user_id'])

@router.get("/msr/details/cu/warehouse/{warehouse_id}")
@limiter.limit("30/minute")
async def fetch_cu_warehouse(request: Request, warehouse_id: str, current_user: dict = Depends(get_current_user)):
    return MSR_CU_DMM_warehouse(warehouse_id)

@router.get("/msr/details/bu/warehouse/{warehouse_id}")
@limiter.limit("30/minute")
async def fetch_cu_warehouse(request: Request, warehouse_id: str, current_user: dict = Depends(get_current_user)):
    return MSR_BU_warehouse(warehouse_id)

@router.post("/warehouse/reentry")
@limiter.limit("30/minute")
async def warehouse_reentry_route(request: Request, data: List[Dict[str, Any]], current_user: dict = Depends(get_current_user)):
    return warehouse_reentry(data, current_user['user_id'])

@router.get("/unhoused/view/{district_id}")
@limiter.limit("30/minute")
async def get_unhoused(request: Request, district_id: int):
    return components_without_warehouse(district_id)

@router.post("/warehouse/entry")
@limiter.limit("30/minute")
async def warehouse_reentry_route(
    request: Request,
    data: List[Dict[str, Any]],
    current_user: dict = Depends(get_current_user)
):
        return warehouse_box_entry(data, current_user["user_id"])
from fastapi import APIRouter,Depends,HTTPException,Path
from core.components import (new_components, ComponentModel,view_paired_cu,view_components, 
                             view_paired_bu,view_paired_cu_sec,
                             view_paired_cu_deo,view_components_sec,view_components_deo,
                             view_paired_bu_deo,view_paired_bu_sec,approve_component_by_sec,approval_queue_sec,
                             view_dmm)
from typing import List
from pydantic import BaseModel
from utils.authtoken import get_current_user
from core.return_ import damaged,view_damaged
from core.msr import get_evm_pairing_data,get_bu_data,get_bu_data_by_user,get_evm_pairing_data_by_user


class PairedCU(BaseModel):
    user_id : int

class PairedBU(BaseModel):
    user_id : int

router = APIRouter()

@router.post("/new")
async def create_new_components(components: List[ComponentModel],order_no:str,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC','DEO', 'FLC Officer']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    else:
        return new_components(components, order_no,current_user['user_id'])

@router.get("/msr/unpaired/{component_type}/{district_id}") #View all components of a specific type in a district if called by DEO, else if SEC all districts
async def cu(component_type:str,district_id:str =Path(...),current_user: dict = Depends(get_current_user)):
    try:
        district_id=int(district_id)
        if current_user['role']=='DEO':
            return view_components_deo(component_type,district_id)
    except (ValueError, TypeError):
        return view_components_sec(component_type)
    
@router.get('/view/unpaired/{component_type}')  #View all components of a specific type
async def view_unpaired(component_type:str,current_user:dict = Depends(get_current_user)):
    return view_components(component_type.upper(),current_user['user_id'])

@router.get("/msr/paired/cu/{district_id}") #View CU+DMM+seals within a district if called by DEO, else if SEC all districts
async def paired_cu(district_id:str=Path(...),current_user: dict = Depends(get_current_user)):
    try:
        district_id = int(district_id)
        if current_user['role'] == 'DEO':
            return view_paired_cu_deo(district_id)
    except (ValueError, TypeError):
        return view_paired_cu_sec()
    
@router.get("/view/paired/cu")  #View CU+DMM+seals
async def get_paired_cu(current_user: dict = Depends(get_current_user)):
    return view_paired_cu(current_user['user_id'])

@router.get("/msr/paired/bu/{district_id}") #View BU within a district if called by DEO, else if SEC all districts
async def paired_bu(district_id: str = Path(...),current_user: dict = Depends(get_current_user)):
    try:
        district_id = int(district_id)

        if current_user['role'] == 'DEO':
            return view_paired_bu_deo(district_id)

    except (ValueError, TypeError):
        return view_paired_bu_sec()
    
@router.get("/view/paired/bu") #To fetch all details of BU including paired components and status
async def get_paired_bu(current_user: dict = Depends(get_current_user)):
    return view_paired_bu(current_user['user_id'])
      
@router.post("/approve")
async def approve_component(serial_numbers: List[str], current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'SEC':
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return approve_component_by_sec(serial_numbers, current_user['user_id'])

@router.get("/pending")
async def pending_approval(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'SEC':
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return approval_queue_sec()

@router.post("/damaged/add")
async def add_damaged(evm_id:str,current_user: dict = Depends(get_current_user)):
    return damaged(evm_id)

@router.get("/damaged/view/{district_id}")
async def damaged_view(district_id:int,current_user: dict = Depends(get_current_user)):
    return view_damaged(district_id)

@router.get("/reserve/dmm")
async def view_reserve_dmm(current_user: dict = Depends(get_current_user)):
    return view_dmm(current_user['user_id'])

@router.get("/msr/details/cu")
async def get_msr_details_cu():
    return get_evm_pairing_data()

@router.get("/msr/details/bu")
async def get_msr_details_bu():
    return get_bu_data()

@router.get("/msr/details/bu/user/")
async def get_msr_details_bu_by_user(current_user: dict = Depends(get_current_user)):
    return get_bu_data_by_user(current_user['user_id'])


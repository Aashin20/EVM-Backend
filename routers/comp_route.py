from fastapi import APIRouter,Depends,HTTPException,Path
from core.components import (new_components, ComponentModel,view_paired_cu,view_components, 
                             view_paired_bu,view_paired_cu_sec,
                             view_paired_cu_deo,view_components_sec,view_components_deo,
                             view_paired_bu_deo,view_paired_bu_sec)
from typing import List
from pydantic import BaseModel
from utils.authtoken import get_current_user


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

@router.get("/view/unpaired/{component_type}/{district_id}")
async def cu(component_type:str,district_id:str =Path(...),current_user: dict = Depends(get_current_user)):
    try:
        district_id=int(district_id)
        if current_user['role']=='DEO':
            return view_components_deo(component_type,district_id)
        else:
            return view_components(component_type.upper(),current_user['user_id'])
    except (ValueError, TypeError):
        return view_components_sec(component_type)
    
    

@router.get("/view/paired/cu/{district_id}")
async def paired_cu(district_id:int,current_user: dict = Depends(get_current_user)):
    if current_user['role']=='SEC':
        return view_paired_cu_sec()
    elif current_user['role'] == 'DEO':
        return view_paired_cu_deo(district_id)
    else:
        return view_paired_cu(current_user['user_id'])

@router.get("/view/paired/bu/{district_id}")
async def paired_bu(district_id: str = Path(...),current_user: dict = Depends(get_current_user)):
    try:
        district_id = int(district_id)

        if current_user['role'] == 'DEO':
            return view_paired_bu_deo(district_id)
        else:
            return view_paired_bu(current_user['user_id'])

    except (ValueError, TypeError):
        return view_paired_bu_sec()
      
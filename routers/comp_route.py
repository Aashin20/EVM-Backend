from fastapi import APIRouter,Depends,HTTPException
from core.components import new_components, ComponentModel,view_paired_cu,view_components, view_paired_bu
from typing import List
from pydantic import BaseModel
from utils.authtoken import get_current_user


class PairedCU(BaseModel):
    user_id : int

class PairedBU(BaseModel):
    user_id : int

router = APIRouter()

@router.post("/new")
def create_new_components(components: List[ComponentModel], current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC','DEO', 'FLC Officer']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    else:
        return new_components(components, current_user['user_id'])

@router.get("/view/unpaired/{component_type}")
async def cu(component_type:str,current_user: dict = Depends(get_current_user)):
    return view_components(component_type.upper(),current_user['user_id'])

@router.get("/view/paired/cu")
async def paired_cu(current_user: dict = Depends(get_current_user)):
    return view_paired_cu(current_user['user_id'])

@router.get("/view/paired/bu")
async def paired_bu(current_user: dict = Depends(get_current_user)):
    return view_paired_bu(current_user['user_id'])
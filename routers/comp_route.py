from fastapi import APIRouter
from core.components import new_components, ComponentModel,view_paired_cu,view_components, view_paired_bu
from typing import List
from pydantic import BaseModel

class PairedCU(BaseModel):
    user_id : int

class PairedBU(BaseModel):
    user_id : int

router = APIRouter()

@router.post("/new")
def create_new_components(components: List[ComponentModel]):
    return new_components(components)

@router.get("/view/unpaired/{user_id}/{component_type}")
async def cu(component_type:str,user_id: int):
    return view_components(component_type.upper(),user_id)

@router.get("/view/paired/cu/{user_id}")
async def paired_cu(user_id: int):
    return view_paired_cu(user_id)

@router.get("/view/paired/bu/{user_id}")
async def paired_bu(user_id: int):
    return view_paired_bu(user_id)
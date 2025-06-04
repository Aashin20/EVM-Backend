from fastapi import APIRouter
from core.components import new_components, ComponentModel,view_paired_cu,view_components
from typing import List

router = APIRouter()

@router.post("/new")
def create_new_components(components: List[ComponentModel]):
    return new_components(components)

@router.get("/view/{user_id}/{component_type}")
async def cu(component_type:str,user_id: int):
    return view_components(component_type.upper(),user_id)


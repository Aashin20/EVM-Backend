from fastapi import APIRouter
from core.components import new_component, ComponentModel,view_cu

router = APIRouter()

@router.post("/new")
async def add_component(details: ComponentModel):
    return new_component(details)

@router.get("/cu/{district_id}")
async def cu(district_id: int):
    return view_cu(district_id)
from fastapi import APIRouter
from core.components import new_component, ComponentModel

router = APIRouter()

@router.post("/new")
async def add_component(details: ComponentModel):
    return new_component(details)
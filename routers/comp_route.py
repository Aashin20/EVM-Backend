from fastapi import APIRouter
from core.components import new_components, ComponentModel,view_cu
from typing import List

router = APIRouter()

@router.post("/new")
def create_new_components(components: List[ComponentModel]):
    return new_components(components)

@router.get("/cu/{user_id}")
async def cu(user_id: int):
    return view_cu(user_id)
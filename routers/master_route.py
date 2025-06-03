from fastapi import APIRouter   
from core.user import register, RegisterModel, view_users,UpdateUserModel,edit_user

router = APIRouter()

@router.post("/user/create")
async def register_user(details: RegisterModel):
    return register(details)


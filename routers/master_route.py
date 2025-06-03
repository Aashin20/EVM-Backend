from fastapi import APIRouter   
from core.user import register, RegisterModel, view_users,UpdateUserModel,edit_user

router = APIRouter()

@router.post("/user/create")
async def register_user(details: RegisterModel):
    return register(details)

@router.get("/user/view") #SEC ONLY
async def view():
    return view_users()

@router.post("/user/edit")
async def edit(details: UpdateUserModel):
    return edit_user(details)
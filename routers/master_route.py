from fastapi import APIRouter   
from core.user import register, RegisterModel, view_users,UpdateUserModel,edit_user
from utils.authtoken import get_current_user
from fastapi import Depends

router = APIRouter()

@router.post("/user/create")
async def register_user(details: RegisterModel, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status" : 401, "message": "Unauthorized access"}
    else:
        return register(details)

@router.get("/user/view") #SEC ONLY
async def view(current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return view_users()

@router.post("/user/edit")
async def edit(details: UpdateUserModel,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    else:
        return edit_user(details)
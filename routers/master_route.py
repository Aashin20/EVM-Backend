from fastapi import APIRouter   
from core.user import register, RegisterModel, view_users,UpdateUserModel,edit_user,add_ps,approve_ps,reject_ps,view_ps,PollingStationModel,get_ps
from utils.authtoken import get_current_user
from fastapi import Depends
from typing import List

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

@router.post("/ps/add")
async def add_ps_endpoint(data: List[PollingStationModel],current_user: dict = Depends(get_current_user)):
    return add_ps(data)

@router.get("/ps/pending/{district_id}")
async def ps_view(district_id: int,current_user: dict = Depends(get_current_user)):
    return view_ps(district_id)

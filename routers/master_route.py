from fastapi import APIRouter   
from core.user import (register, RegisterModel, view_users,UpdateUserModel,
                       edit_user,add_ps,approve_ps,reject_ps,view_ps,
                       PollingStationModel,get_ps,mass_deactivate)
from core.allotment import view_all_allotments_deo
from utils.authtoken import get_current_user
from fastapi import Depends
from typing import List
from core.components import get_details

router = APIRouter()

@router.post("/user/create")
async def register_user(details: RegisterModel,current_user: dict = Depends(get_current_user)):
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

@router.post("/ps/approve")
async def ps_approve(ps_ids: List[int],current_user: dict = Depends(get_current_user)):
    return approve_ps(ps_ids, current_user['user_id'])

@router.post("/ps/reject")
async def ps_reject(ps_ids: List[int], current_user: dict = Depends(get_current_user)):
    return reject_ps(ps_ids, current_user['user_id'])

@router.get("/ps/view/{local_body_id}")
async def view(local_body_id:str,current_user: dict = Depends(get_current_user)):
    return get_ps(local_body_id)

@router.get("/dashboard")
async def dash(current_user: dict = Depends(get_current_user)):
    return get_details(current_user['user_id'])

@router.get("/toggle/{role}")
async def deactivate(role:str,current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['Developer', 'SEC']:
        return {"status": 401, "message": "Unauthorized access"}
    return mass_deactivate(role,current_user['user_id'])

@router.get("/dashboard/{district_id}")
async def view_deo_allotments(district_id: int):
    return view_all_allotments_deo(district_id)
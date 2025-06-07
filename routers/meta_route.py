from fastapi import APIRouter, Depends
from core.user import get_local_body,get_districts,get_panchayath,get_user,get_RO,get_evm_from_ps
from utils.authtoken import get_current_user
from typing import List

router = APIRouter()

@router.get("/district/{district_id}/{type}")
async def local_body(district_id:int,type: str,current_user: dict = Depends(get_current_user)):
    return get_local_body(district_id,type)

@router.get("/bodies/district")
async def district(current_user: dict = Depends(get_current_user)):
    return get_districts()

@router.get("/panchayat/{block_id}")
async def panchayath(block_id: str,current_user: dict = Depends(get_current_user)):
    return get_panchayath(block_id)

@router.get("/user/{local_body_id}")
async def user(local_body_id: str, current_user: dict = Depends(get_current_user)):
    return get_user(local_body_id)

@router.get("/RO/{local_body_id}")
async def RO(local_body_id:str,current_user: dict = Depends(get_current_user)):
    return get_RO(local_body_id)

@router.get("/ps/{local_body_id}")
async def evm_from_ps(local_body_id:str,current_user: dict = Depends(get_current_user)):
    return get_evm_from_ps(local_body_id)
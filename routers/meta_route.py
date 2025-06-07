from fastapi import APIRouter, Depends
from core.user import get_local_body,get_districts,get_panchayath,get_user,get_RO
from utils.authtoken import get_current_user

router = APIRouter()

@router.get("/district/{district_id}/{type}")
async def local_body(district_id:int,type: str,current_user: dict = Depends(get_current_user)):
    return get_local_body(district_id,type)

@router.get("/bodies/district")
async def district(current_user: dict = Depends(get_current_user)):
    return get_districts()

@router.get("/panchayath/{block_id}")
async def panchayath(block_id: str,current_user: dict = Depends(get_current_user)):
    return get_panchayath(block_id)

from fastapi import APIRouter, Depends
from core.user import get_local_body
from utils.authtoken import get_current_user

router = APIRouter()

@router.get("/district/{district_id}/{type}")
async def local_body(district_id: int,type: str, current_user: dict = Depends(get_current_user)):
    return get_local_body(district_id,type)
from core.return_ import status_change,decommission_evms,DecommissionModel
from utils.authtoken import get_current_user
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()


@router.get('/{local_body_id}/{status}')
async def to_polling(local_body_id:str,status:str,current_user: dict = Depends(get_current_user)):
    return status_change(local_body_id,status)

@router.post('/decommission')
async def evm_decommission(data: DecommissionModel):
    return decommission_evms(data)
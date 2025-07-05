from core.return_ import status_change,decommission_evms,DecommissionModel
from utils.authtoken import get_current_user
from fastapi import APIRouter, Depends
from typing import List
from core.return_ import return_pending,return_queue,return_to_ecil
router = APIRouter()


@router.get('/change/{local_body_id}/{status}') #Used to change status of EVMs(Polling,Polled,Counted)
async def to_polling(local_body_id:str,status:str,current_user: dict = Depends(get_current_user)):
    return status_change(local_body_id,status)

@router.post('/decommission')
async def evm_decommission(data: DecommissionModel,current_user: dict = Depends(get_current_user)):
    return decommission_evms(data)

@router.get("/return/pending")
async def return_pending_send(current_user: dict = Depends(get_current_user)):
    return return_pending(current_user['user_id'])

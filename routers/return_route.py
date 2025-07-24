from core.return_ import status_change, decommission_evms, DecommissionModel
from utils.authtoken import get_current_user
from fastapi import APIRouter, Depends, Request
from typing import List
from core.return_ import return_pending, return_queue, return_to_ecil
from utils.rate_limiter import limiter

router = APIRouter()

@router.get('/change/{local_body_id}/{status}') #Used to change status of EVMs(Polling,Polled,Counted)
@limiter.limit("30/minute")
async def to_polling(request: Request, local_body_id: str, status: str, current_user: dict = Depends(get_current_user)):
    return status_change(local_body_id, status)

@router.post('/decommission')
@limiter.limit("30/minute")
async def evm_decommission(request: Request, data: DecommissionModel, current_user: dict = Depends(get_current_user)):
    return decommission_evms(data)

@router.get("/return/pending")
@limiter.limit("30/minute")
async def return_pending_send(request: Request, current_user: dict = Depends(get_current_user)):
    return return_pending(current_user['user_id'])

@router.get("/return/queue")
@limiter.limit("30/minute")
async def return_queue_view(request: Request, current_user: dict = Depends(get_current_user)):
    return return_queue()

@router.get("/return/to_ecil/{comp_serial}")
@limiter.limit("30/minute")
async def return_to_ecil_route(request: Request, comp_serial: str, current_user: dict = Depends(get_current_user)):
    return return_to_ecil(comp_serial)

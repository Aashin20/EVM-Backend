from fastapi import APIRouter, Depends, HTTPException, Body, Query, Form, UploadFile, File, Request
from core.allotment import (reject_allotment, approve_allotment,
                            approval_queue, view_pending_allotment_components,
                            view_pending_allotments, pending, remove_pending_allotment,
                            view_temporary, return_temporary_allotment)
from core.commissioning import evm_commissioning, EVMCommissioningModel, view_reserve, allot_reserve_evm_to_polling_station, ReserveEVMCommissioningModel
from core.create_allotment import create_allotment, AllotmentModel
from utils.authtoken import get_current_user
from typing import List, Optional
import json
from fastapi import BackgroundTasks
from utils.rate_limiter import limiter

router = APIRouter()

@router.post("/")
@limiter.limit("10/minute")
async def allot_evm(
    request: Request,
    background_tasks: BackgroundTasks,  
    pending_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    content_type = request.headers.get("content-type", "")
    
    if content_type.startswith("application/json"):
        body = await request.json()
        data = AllotmentModel(**body)
        pdf_bytes = None

    elif content_type.startswith("multipart/form-data"):
        form_data = await request.form()
        
        if 'data' not in form_data:
            raise HTTPException(status_code=400, detail="Missing 'data' field in form")
        
        try:
            allotment_data = json.loads(form_data['data'])
            data = AllotmentModel(**allotment_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON data")
        
        pdf_bytes = None
        if 'treasury_receipt_pdf' in form_data:
            treasury_receipt_pdf = form_data['treasury_receipt_pdf']
            if treasury_receipt_pdf.filename: 
                pdf_bytes = await treasury_receipt_pdf.read()
                print(f"[ENDPOINT] Received treasury receipt PDF: {treasury_receipt_pdf.filename}, size: {len(pdf_bytes)} bytes")
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")
    
    return create_allotment(
            background_tasks=background_tasks, 
            evm=data,                         
            from_user_id=current_user['user_id'],            
            pending_allotment_id=pending_id,  
            treasury_receipt_pdf=pdf_bytes    
        )

@router.get("/pending/view")
@limiter.limit("30/minute")
async def pending_view(request: Request, current_user: dict = Depends(get_current_user)):
    return view_pending_allotments(current_user['user_id'])

@router.post("/pending")
@limiter.limit("30/minute")
async def pending_create(request: Request, data: AllotmentModel, current_user: dict = Depends(get_current_user)):
    return pending(data, current_user['user_id'])

@router.get("/pending/components/{pending_id}")
@limiter.limit("30/minute")
async def view_pending_comp(request: Request, pending_id: int, current_user: dict = Depends(get_current_user)):
    return view_pending_allotment_components(pending_id, current_user['user_id'])

@router.get("/pending/remove/{pending_id}")
@limiter.limit("30/minute")
async def remove_pending(request: Request, pending_id: int, current_user: dict = Depends(get_current_user)):
    return remove_pending_allotment(pending_id, current_user['user_id'])

@router.get("/approve/{allotment_id}")
@limiter.limit("30/minute")
async def approve(request: Request, allotment_id: int, current_user: dict = Depends(get_current_user)):  
    return approve_allotment(allotment_id, current_user['user_id'])

@router.get("/reject/{allotment_id}/{reject_reason}")
@limiter.limit("30/minute")
async def reject(request: Request, allotment_id: int, reject_reason: str, current_user: dict = Depends(get_current_user)):  
    return reject_allotment(allotment_id, reject_reason, current_user['user_id'])

@router.get("/queue/")
@limiter.limit("30/minute")
async def queue(request: Request, current_user: dict = Depends(get_current_user)):
    return approval_queue(current_user['user_id'])

@router.post("/commission")
@limiter.limit("30/minute")
async def evm_commissioning_route(request: Request, background_tasks: BackgroundTasks, data: List[EVMCommissioningModel] = Body(...), current_user: dict = Depends(get_current_user)):
    return evm_commissioning(background_tasks,data, current_user['user_id'])

@router.get("/reserve")
@limiter.limit("30/minute")
async def reserve_view(request: Request, current_user: dict = Depends(get_current_user)):
    return view_reserve(current_user['user_id'])

@router.post("/reserve/allot")
@limiter.limit("30/minute")
async def allot_reserve_evm(request: Request, data: ReserveEVMCommissioningModel, psno: int, current_user: dict = Depends(get_current_user)):
    return allot_reserve_evm_to_polling_station(data, psno, current_user['user_id'])

@router.get("/temporary")
async def view_temporary_allotments(request: Request, current_user: dict = Depends(get_current_user)):
    return view_temporary(current_user['user_id'])

@router.post("/temporary/return/")
@limiter.limit("30/minute")
async def return_temporary(request: Request, allotment_id: int, return_date: str, current_user: dict = Depends(get_current_user)):
    if not allotment_id or not return_date:
        raise HTTPException(status_code=400, detail="Allotment ID and return date are required")
    return return_temporary_allotment(allotment_id, return_date, current_user['user_id'])

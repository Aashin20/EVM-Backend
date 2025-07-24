from fastapi import APIRouter, Query, Depends, Request
from utils.authtoken import get_current_user
from typing import Optional
from datetime import date
from core.logs import (
    get_allotment_logs_data,
    get_component_logs_data,
    get_pairing_logs_data,
    get_flc_record_logs_data,
    get_flc_bu_logs_data,
    get_all_logs_data
)
from core.allotment import view_allotment_items
from fastapi.exceptions import HTTPException
from utils.rate_limiter import limiter

router = APIRouter()


@router.get("/allotments")
@limiter.limit("30/minute")
async def get_allotment_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):

    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_allotment_logs_data(page, page_size, start_date, end_date)


@router.get("/components")
@limiter.limit("30/minute")
async def get_component_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_component_logs_data(page, page_size, start_date, end_date)


@router.get("/pairings")
@limiter.limit("30/minute")
async def get_pairing_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_pairing_logs_data(page, page_size, start_date, end_date)


@router.get("/flc-records")
@limiter.limit("30/minute")
async def get_flc_record_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_flc_record_logs_data(page, page_size, start_date, end_date)


@router.get("/flc-ballot-units")
@limiter.limit("30/minute")
async def get_flc_bu_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_flc_bu_logs_data(page, page_size, start_date, end_date)


@router.get("/all")
@limiter.limit("30/minute")
async def get_all_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
 
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_all_logs_data(page, page_size, start_date, end_date)

@router.get("/allotment-items/{allotment_id}")
@limiter.limit("30/minute")
async def view_allotment_items_route(
    request: Request,
    allotment_id: int,
    current_user: dict = Depends(get_current_user)
):
    return view_allotment_items(allotment_id)
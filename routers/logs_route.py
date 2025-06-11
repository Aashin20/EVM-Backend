from fastapi import APIRouter, Query,Depends
from utils.authtoken import get_current_user
from typing import Optional
from datetime import date
from core.logs import (
    get_allotment_logs_data,
    get_allotment_item_logs_data,
    get_component_logs_data,
    get_pairing_logs_data,
    get_flc_record_logs_data,
    get_flc_bu_logs_data,
    get_all_logs_data
)
from fastapi.exceptions import HTTPException


router = APIRouter()


@router.get("/allotments")
def get_allotment_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get allotment logs with pagination and date filtering"""
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_allotment_logs_data(page, page_size, start_date, end_date)


@router.get("/allotment-items")
def get_allotment_item_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get allotment item logs with pagination and date filtering"""
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_allotment_item_logs_data(page, page_size, start_date, end_date)


@router.get("/components")
def get_component_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get EVM component logs with pagination and date filtering"""
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_component_logs_data(page, page_size, start_date, end_date)


@router.get("/pairings")
def get_pairing_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get pairing record logs with pagination and date filtering"""
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_pairing_logs_data(page, page_size, start_date, end_date)


@router.get("/flc-records")
def get_flc_record_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get FLC record logs with pagination and date filtering"""
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_flc_record_logs_data(page, page_size, start_date, end_date)


@router.get("/flc-ballot-units")
def get_flc_bu_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get FLC ballot unit logs with pagination and date filtering"""
    if current_user['role'] not in ['SEC']:
        raise HTTPException(status_code=401, detail="Unauthorized access")
    return get_flc_bu_logs_data(page, page_size, start_date, end_date)


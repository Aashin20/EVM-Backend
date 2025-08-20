from fastapi import APIRouter, Depends, Request
from core.user import (get_local_body, get_districts, get_panchayath,
                       get_user, get_RO, get_evm_from_ps, get_warehouse, get_deo)
from utils.authtoken import get_current_user
from typing import List
from utils.rate_limiter import limiter
from utils.cache_decorator import cache_response

router = APIRouter()

@router.get("/district/{district_id}/{type}")
@limiter.limit("30/minute")
@cache_response(expire=3600, key_prefix="meta_local_body", include_user=False)
async def local_body(request: Request, district_id: int, type: str,current_user: dict = Depends(get_current_user)):
    return get_local_body(district_id, type)

@router.get("/bodies/district")
@cache_response(expire=3600, key_prefix="meta_district", include_user=False)
@limiter.limit("30/minute")
async def district(request: Request, current_user: dict = Depends(get_current_user)):
    return get_districts()

@router.get("/panchayat/{block_id}")
@cache_response(expire=3600, key_prefix="meta_panchayath", include_user=False)
@limiter.limit("30/minute")
async def panchayath(request: Request, block_id: str, current_user: dict = Depends(get_current_user)):
    return get_panchayath(block_id)

@router.get("/user/{local_body_id}")
@cache_response(expire=3600, key_prefix="meta_get_user", include_user=False)
@limiter.limit("30/minute")
async def user(request: Request, local_body_id: str, current_user: dict = Depends(get_current_user)):
    return get_user(local_body_id)

@router.get("/RO/{local_body_id}")
@cache_response(expire=3600, key_prefix="meta_get_ro", include_user=False)
@limiter.limit("30/minute")
async def RO(request: Request, local_body_id: str, current_user: dict = Depends(get_current_user)):
    return get_RO(local_body_id)

@router.get("/ps/{local_body_id}")
@cache_response(expire=1800, key_prefix="allot_get_evm", include_user=True)
@limiter.limit("30/minute")
async def evm_from_ps(request: Request, local_body_id: str, current_user: dict = Depends(get_current_user)):
    return get_evm_from_ps(local_body_id)

@router.get("/warehouses/{district_id}")
@cache_response(expire=3600, key_prefix="meta_warehouse", include_user=False)
@limiter.limit("30/minute")
async def warehouse(request: Request, district_id: int, current_user: dict = Depends(get_current_user)):
    return get_warehouse(district_id)

@router.get("/deo")
@cache_response(expire=3600, key_prefix="meta_deo", include_user=False)
@limiter.limit("30/minute")
async def get_de0_from_district_id(request: Request, current_user: dict = Depends(get_current_user)):
    return get_deo()
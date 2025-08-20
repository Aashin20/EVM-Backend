from fastapi import APIRouter, Request, Depends, BackgroundTasks
from typing import Optional, List
from fastapi import Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import aliased
from core.paginated import MSR_CU_DMM_PAGINATED, MSRFilters, MSRResponse,MSR_BU_PAGINATED, MSRBUFilters, MSRBUResponse
from utils.rate_limiter import limiter
from utils.authtoken import get_current_user
from utils.cache_decorator import cache_response


router = APIRouter()

@router.get("/details/cu", response_model=MSRResponse)
@limiter.limit("30/minute")
@cache_response(expire=3600, key_prefix="comp_msr_sec_cu", include_user=True)
async def get_msr_details_cu_paginated(
    request: Request,
    limit: int = Query(default=500, le=1000, ge=1),
    cursor: Optional[str] = Query(default=None),
    direction: str = Query(default="next", regex="^(next|prev)$"),
    # Filter parameters
    cu_dmm_received: Optional[str] = Query(default=None),
    date_of_receipt: Optional[date] = Query(default=None),
    date_of_receipt_start: Optional[date] = Query(default=None),
    date_of_receipt_end: Optional[date] = Query(default=None),
    control_unit_no: Optional[str] = Query(default=None),
    cu_manufacture_date: Optional[str] = Query(default=None),
    dmm_no: Optional[str] = Query(default=None),
    dmm_manufacture_date: Optional[str] = Query(default=None),
    dmm_seal_no: Optional[str] = Query(default=None),
    cu_pink_paper_seal_no: Optional[str] = Query(default=None),
    flc_date: Optional[date] = Query(default=None),
    flc_date_start: Optional[date] = Query(default=None),
    flc_date_end: Optional[date] = Query(default=None),
    flc_status: Optional[str] = Query(default=None),
    cu_box_no: Optional[str] = Query(default=None),
    cu_warehouse: Optional[str] = Query(default=None),
    present_status_dmm: Optional[str] = Query(default=None),
    present_status_cu: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    
    filters = MSRFilters(
        cu_dmm_received=cu_dmm_received,
        date_of_receipt=date_of_receipt,
        date_of_receipt_start=date_of_receipt_start,
        date_of_receipt_end=date_of_receipt_end,
        control_unit_no=control_unit_no,
        cu_manufacture_date=cu_manufacture_date,
        dmm_no=dmm_no,
        dmm_manufacture_date=dmm_manufacture_date,
        dmm_seal_no=dmm_seal_no,
        cu_pink_paper_seal_no=cu_pink_paper_seal_no,
        flc_date=flc_date,
        flc_date_start=flc_date_start,
        flc_date_end=flc_date_end,
        flc_status=flc_status,
        cu_box_no=cu_box_no,
        cu_warehouse=cu_warehouse,
        present_status_dmm=present_status_dmm,
        present_status_cu=present_status_cu
    )
    
    return MSR_CU_DMM_PAGINATED(limit, cursor, direction, filters)

@router.get("/details/bu", response_model=MSRBUResponse)
@limiter.limit("30/minute")
@cache_response(expire=3600, key_prefix="comp_msr_sec_bu", include_user=True)
async def get_msr_details_bu_paginated(
    request: Request,
    limit: int = Query(default=500, le=1000, ge=1),
    cursor: Optional[str] = Query(default=None),
    direction: str = Query(default="next", regex="^(next|prev)$"),
    # Filter parameters
    bu_received_from: Optional[str] = Query(default=None),
    date_of_receipt: Optional[date] = Query(default=None),
    date_of_receipt_start: Optional[date] = Query(default=None),
    date_of_receipt_end: Optional[date] = Query(default=None),
    ballot_unit_no: Optional[str] = Query(default=None),
    year_of_manufacture: Optional[str] = Query(default=None),
    flc_date: Optional[date] = Query(default=None),
    flc_date_start: Optional[date] = Query(default=None),
    flc_date_end: Optional[date] = Query(default=None),
    flc_status: Optional[str] = Query(default=None),
    bu_box_no: Optional[str] = Query(default=None),
    bu_warehouse: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    
    filters = MSRBUFilters(
        bu_received_from=bu_received_from,
        date_of_receipt=date_of_receipt,
        date_of_receipt_start=date_of_receipt_start,
        date_of_receipt_end=date_of_receipt_end,
        ballot_unit_no=ballot_unit_no,
        year_of_manufacture=year_of_manufacture,
        flc_date=flc_date,
        flc_date_start=flc_date_start,
        flc_date_end=flc_date_end,
        flc_status=flc_status,
        bu_box_no=bu_box_no,
        bu_warehouse=bu_warehouse
    )
    
    return MSR_BU_PAGINATED(limit, cursor, direction, filters)
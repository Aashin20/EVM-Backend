from typing import Optional, List, Dict, Any
from datetime import datetime, date
from math import ceil
from models.logs import EVMComponentLogs, AllotmentItemLogs, AllotmentLogs, PairingRecordLogs, FLCBallotUnitLogs, FLCRecordLogs
from core.db import Database
from models.users import User, LocalBody, District, Warehouse
from models.evm import PollingStation


def get_paginated_response(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size)
    }


def apply_date_filter(query, model, start_date: Optional[date], end_date: Optional[date]):
    timestamp_field = None
    
    if hasattr(model, 'created_at'):
        timestamp_field = model.created_at
    elif hasattr(model, 'created_on'):
        timestamp_field = model.created_on
    elif hasattr(model, 'flc_date'):
        timestamp_field = model.flc_date
    
    if timestamp_field is not None:
        if start_date:
            query = query.filter(timestamp_field >= start_date)
        if end_date:
            query = query.filter(timestamp_field <= end_date)
    
    return query



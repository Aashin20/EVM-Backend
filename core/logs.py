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



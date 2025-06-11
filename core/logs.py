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


def get_user_name(db, user_id: int):
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user.username if user else None


def get_district_name(db, district_id: int):
    if not district_id:
        return None
    district = db.query(District).filter(District.id == district_id).first()
    return district.name if district else None


def get_local_body_name(db, local_body_id: str):
    if not local_body_id:
        return None
    local_body = db.query(LocalBody).filter(LocalBody.id == local_body_id).first()
    return local_body.name if local_body else None


def get_warehouse_name(db, warehouse_id: str):
    if not warehouse_id:
        return None
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    return warehouse.name if warehouse else None


def get_polling_station_name(db, polling_station_id: int):
    if not polling_station_id:
        return None
    ps = db.query(PollingStation).filter(PollingStation.id == polling_station_id).first()
    return ps.name if ps else None


def get_allotment_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        query = db.query(AllotmentLogs)
        query = apply_date_filter(query, AllotmentLogs, start_date, end_date)
        result = get_paginated_response(query, page, page_size)
        
        formatted_items = []
        for log in result["items"]:
            formatted_items.append({
                "id": log.id,
                "allotment_type": log.allotment_type.value if log.allotment_type else None,
                "from_user": get_user_name(db, log.from_user_id),
                "to_user": get_user_name(db, log.to_user_id),
                "from_district": get_district_name(db, log.from_district_id),
                "to_district": get_district_name(db, log.to_district_id),
                "from_local_body": get_local_body_name(db, log.from_local_body_id),
                "to_local_body": get_local_body_name(db, log.to_local_body_id),
                "reject_reason": log.reject_reason,
                "status": log.status,
                "created_at": log.created_at,
                "approved_at": log.approved_at,
                "is_temporary": log.is_temporary,
                "temporary_reason": log.temporary_reason
            })
        
        result["items"] = formatted_items
        return result


def get_allotment_item_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        query = db.query(AllotmentItemLogs).join(AllotmentLogs)
        query = apply_date_filter(query, AllotmentLogs, start_date, end_date)
        result = get_paginated_response(query, page, page_size)
        
        formatted_items = []
        for item in result["items"]:
            component = db.query(EVMComponentLogs).filter(EVMComponentLogs.id == item.evm_component_id).first()
            formatted_items.append({
                "id": item.id,
                "allotment_id": item.allotment_id,
                "component_serial": component.serial_number if component else None,
                "component_type": component.component_type.value if component and component.component_type else None,
                "remarks": item.remarks
            })
        
        result["items"] = formatted_items
        return result


def get_component_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        query = db.query(EVMComponentLogs)
        query = apply_date_filter(query, EVMComponentLogs, start_date, end_date)
        result = get_paginated_response(query, page, page_size)
        
        formatted_items = []
        for log in result["items"]:
            formatted_items.append({
                "id": log.id,
                "serial_number": log.serial_number,
                "component_type": log.component_type.value if log.component_type else None,
                "status": log.status,
                "is_verified": log.is_verified,
                "dom": log.dom,
                "box_no": log.box_no,
                "current_user": get_user_name(db, log.current_user_id),
                "current_warehouse": get_warehouse_name(db, log.current_warehouse_id),
                "created_on": log.created_on
            })
        
        result["items"] = formatted_items
        return result


def get_pairing_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        query = db.query(PairingRecordLogs)
        query = apply_date_filter(query, PairingRecordLogs, start_date, end_date)
        result = get_paginated_response(query, page, page_size)
        
        formatted_items = []
        for log in result["items"]:
            formatted_items.append({
                "id": log.id,
                "evm_id": log.evm_id,
                "polling_station": get_polling_station_name(db, log.polling_station_id),
                "created_by": get_user_name(db, log.created_by_id),
                "created_at": log.created_at,
                "completed_by": get_user_name(db, log.completed_by_id),
                "completed_at": log.completed_at
            })
        
        result["items"] = formatted_items
        return result


def get_flc_record_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        query = db.query(FLCRecordLogs)
        query = apply_date_filter(query, FLCRecordLogs, start_date, end_date)
        result = get_paginated_response(query, page, page_size)
        
        formatted_items = []
        for log in result["items"]:
            cu = db.query(EVMComponentLogs).filter(EVMComponentLogs.id == log.cu_id).first()
            dmm = db.query(EVMComponentLogs).filter(EVMComponentLogs.id == log.dmm_id).first()
            dmm_seal = db.query(EVMComponentLogs).filter(EVMComponentLogs.id == log.dmm_seal_id).first()
            pink_seal = db.query(EVMComponentLogs).filter(EVMComponentLogs.id == log.pink_paper_seal_id).first()
            
            formatted_items.append({
                "id": log.id,
                "cu_serial": cu.serial_number if cu else None,
                "dmm_serial": dmm.serial_number if dmm else None,
                "dmm_seal_serial": dmm_seal.serial_number if dmm_seal else None,
                "pink_paper_seal_serial": pink_seal.serial_number if pink_seal else None,
                "box_no": log.box_no,
                "passed": log.passed,
                "remarks": log.remarks,
                "flc_by": get_user_name(db, log.flc_by_id),
                "flc_date": log.flc_date
            })
        
        result["items"] = formatted_items
        return result


def get_flc_bu_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        query = db.query(FLCBallotUnitLogs)
        query = apply_date_filter(query, FLCBallotUnitLogs, start_date, end_date)
        result = get_paginated_response(query, page, page_size)
        
        formatted_items = []
        for log in result["items"]:
            component = db.query(EVMComponentLogs).filter(EVMComponentLogs.id == log.bu_id).first()
            formatted_items.append({
                "id": log.id,
                "bu_serial": component.serial_number if component else None,
                "box_no": log.box_no,
                "passed": log.passed,
                "remarks": log.remarks,
                "flc_by": get_user_name(db, log.flc_by_id),
                "flc_date": log.flc_date
            })
        
        result["items"] = formatted_items
        return result


def get_all_logs_data(page: int, page_size: int, start_date: Optional[date], end_date: Optional[date]):
    with Database.get_session() as db:
        all_logs = []
        
        # Get all log types with their respective timestamp fields
        log_configs = [
            ("allotment", AllotmentLogs, "created_at"),
            ("component", EVMComponentLogs, "created_on"),
            ("pairing", PairingRecordLogs, "created_at"),
            ("flc_record", FLCRecordLogs, "flc_date"),
            ("flc_bu", FLCBallotUnitLogs, "flc_date")
        ]
        
        for log_type, model, timestamp_field in log_configs:
            query = db.query(model)
            query = apply_date_filter(query, model, start_date, end_date)
            
            for log in query.all():
                all_logs.append({
                    "type": log_type,
                    "id": log.id,
                    "created_at": getattr(log, timestamp_field, None),
                    "data": log
                })
        
        # Sort by timestamp
        all_logs.sort(key=lambda x: x['created_at'] or datetime.min, reverse=True)
        
        # Apply pagination
        total = len(all_logs)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_logs = all_logs[start:end]
        
        return {
            "items": [{"type": log["type"], "id": log["id"], "created_at": log["created_at"]} for log in paginated_logs],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": ceil(total / page_size)
        }
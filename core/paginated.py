from typing import Optional, List
from fastapi import Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date
from sqlalchemy import and_, or_, func, text, Date, case, exists
from sqlalchemy.orm import aliased
from core.db import Database
from models.evm import EVMComponent, EVMComponentType, PairingRecord, FLCRecord
from models.users import User, Warehouse
from typing import Optional, List
from fastapi import Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date
from sqlalchemy import and_, or_, func, text, Date
from sqlalchemy.orm import aliased
from sqlalchemy.orm import aliased, selectinload, joinedload
from sqlalchemy import and_, select, case, func
from datetime import datetime
from core.db import Database
from models.evm import EVMComponent, EVMComponentType, PairingRecord, FLCRecord, AllotmentItem, Allotment, FLCBallotUnit
from models.users import User, Warehouse
from sqlalchemy import func, text
from typing import Optional, List
from fastapi import Query, HTTPException
from pydantic import BaseModel
from datetime import datetime, date
from sqlalchemy import and_, func, text, Date, literal, String
from sqlalchemy.orm import aliased
from core.db import Database
from models.evm import EVMComponent, EVMComponentType, PairingRecord, FLCRecord
from models.users import User, Warehouse


class MSRBUFilters(BaseModel):
    bu_received_from: Optional[str] = None
    date_of_receipt: Optional[date] = None
    date_of_receipt_start: Optional[date] = None
    date_of_receipt_end: Optional[date] = None
    ballot_unit_no: Optional[str] = None
    year_of_manufacture: Optional[str] = None
    flc_date: Optional[date] = None
    flc_date_start: Optional[date] = None
    flc_date_end: Optional[date] = None
    flc_status: Optional[str] = None  
    bu_box_no: Optional[str] = None
    bu_warehouse: Optional[str] = None

class MSRBUResponse(BaseModel):
    data: List[dict]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool = False
    total_count: int = 0
    first_serial: Optional[int] = None
    last_serial: Optional[int] = None


class MSRFilters(BaseModel):
    cu_dmm_received: Optional[str] = None
    date_of_receipt: Optional[date] = None
    date_of_receipt_start: Optional[date] = None
    date_of_receipt_end: Optional[date] = None
    control_unit_no: Optional[str] = None
    cu_manufacture_date: Optional[str] = None
    dmm_no: Optional[str] = None
    dmm_manufacture_date: Optional[str] = None
    dmm_seal_no: Optional[str] = None
    cu_pink_paper_seal_no: Optional[str] = None
    flc_date: Optional[date] = None
    flc_date_start: Optional[date] = None
    flc_date_end: Optional[date] = None
    flc_status: Optional[str] = None
    cu_box_no: Optional[str] = None
    cu_warehouse: Optional[str] = None
    present_status_dmm: Optional[str] = None
    present_status_cu: Optional[str] = None

class MSRResponse(BaseModel):
    data: List[dict]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool = False
    total_count: int = 0
    first_serial: Optional[int] = None
    last_serial: Optional[int] = None

def MSR_CU_DMM_PAGINATED(
    limit: int = Query(default=25, le=100, ge=1),
    cursor: Optional[str] = Query(default=None),
    direction: str = Query(default="next", regex="^(next|prev)$"),
    filters: MSRFilters = None
):
    with Database.get_session() as db:
        try:
            is_failed_cu_filter = filters and filters.flc_status == "Failed"
            
            if is_failed_cu_filter:
                return _handle_failed_cu_query(db, limit, cursor, direction, filters)
            else:
                return _handle_regular_query(db, limit, cursor, direction, filters)
                
        except Exception as e:
            print(f"MSR query error: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Query failed")

def _handle_failed_cu_query(db, limit, cursor, direction, filters):
    try:
        latest_flc = db.query(
            FLCRecord.cu_id,
            func.max(FLCRecord.flc_date).label('latest_flc_date')
        ).group_by(FLCRecord.cu_id).subquery()
        
        base_query = db.query(
            EVMComponent.id,
            User.username.label('cu_dmm_received'),
            EVMComponent.date_of_receipt,
            EVMComponent.serial_number.label('control_unit_no'),
            EVMComponent.dom.label('cu_manufacture_date'),
            EVMComponent.box_no.label('cu_box_no'),
            EVMComponent.status.label('present_status_cu'),
            FLCRecord.flc_date,
            Warehouse.name.label('cu_warehouse')
        ).select_from(EVMComponent).join(
            latest_flc, latest_flc.c.cu_id == EVMComponent.id
        ).join(
            FLCRecord, 
            and_(
                FLCRecord.cu_id == EVMComponent.id,
                FLCRecord.flc_date == latest_flc.c.latest_flc_date,
                FLCRecord.passed == False
            )
        ).outerjoin(
            User, User.id == EVMComponent.last_received_from_id
        ).outerjoin(
            Warehouse, Warehouse.id == EVMComponent.current_warehouse_id
        ).filter(
            EVMComponent.component_type == EVMComponentType.CU
        )
        
        base_query = _apply_failed_cu_filters(base_query, filters)
        
        total_count = base_query.count()
        
        if cursor:
            try:
                cursor_id = int(cursor)
                if direction == "next":
                    base_query = base_query.filter(EVMComponent.id > cursor_id)
                else:
                    base_query = base_query.filter(EVMComponent.id < cursor_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor")
        
        if direction == "prev":
            base_query = base_query.order_by(EVMComponent.id.desc())
        else:
            base_query = base_query.order_by(EVMComponent.id.asc())
        
        results = base_query.limit(limit + 1).all()
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]
        
        if direction == "prev":
            results = results[::-1]
        
        formatted_results = []
        for idx, row in enumerate(results, 1):
            formatted_results.append({
                'sl_no': idx,
                'cu_dmm_received': row.cu_dmm_received or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'control_unit_no': row.control_unit_no or "",
                'month_year_manufacture_cu': row.cu_manufacture_date or "",
                'dmm_no': "",
                'month_year_manufacture_dmm': "",
                'dmm_seal_no': "",
                'cu_pink_paper_seal_no': "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                'flc_status': "Failed",
                'cu_box_no': str(row.cu_box_no) if row.cu_box_no else "",
                'cu_warehouse': row.cu_warehouse or "",
                'present_status_dmm': "",
                'present_status_cu': row.present_status_cu or ""
            })
        
        next_cursor = str(results[-1].id) if results and has_more and direction == "next" else None
        prev_cursor = str(results[0].id) if results and cursor and direction == "next" else None
        
        return MSRResponse(
            data=formatted_results,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more=has_more,
            total_count=total_count,
            first_serial=1 if formatted_results else None,
            last_serial=len(formatted_results) if formatted_results else None
        )
    except Exception as e:
        print(f"Failed CU query error: {str(e)}")
        raise

def _handle_regular_query(db, limit, cursor, direction, filters):
    try:
        needs_flc = _needs_flc_join(filters)
        needs_dmm_seal = filters and filters.dmm_seal_no
        needs_pink_seal = filters and filters.cu_pink_paper_seal_no
        
        cu_comp = aliased(EVMComponent)
        
        base_columns = [
            EVMComponent.id,
            User.username.label('cu_dmm_received'),
            func.coalesce(cu_comp.date_of_receipt, EVMComponent.date_of_receipt).label('date_of_receipt'),
            cu_comp.serial_number.label('control_unit_no'),
            cu_comp.dom.label('cu_manufacture_date'),
            cu_comp.box_no.label('cu_box_no'),
            cu_comp.status.label('present_status_cu'),
            EVMComponent.serial_number.label('dmm_no'),
            EVMComponent.dom.label('dmm_manufacture_date'),
            EVMComponent.status.label('present_status_dmm'),
            Warehouse.name.label('cu_warehouse')
        ]
        
        if needs_flc:
            latest_flc = db.query(
                FLCRecord.cu_id,
                func.max(FLCRecord.flc_date).label('latest_flc_date')
            ).group_by(FLCRecord.cu_id).subquery()
            
            base_columns.extend([
                FLCRecord.flc_date,
                FLCRecord.passed.label('flc_status')
            ])
        else:
            base_columns.extend([
                literal(None, Date).label('flc_date'),
                literal(None).label('flc_status')
            ])
        
        if needs_dmm_seal:
            dmm_seal_comp = aliased(EVMComponent)
            base_columns.append(dmm_seal_comp.serial_number.label('dmm_seal_no'))
        else:
            base_columns.append(literal(None, String).label('dmm_seal_no'))
        
        if needs_pink_seal:
            pink_seal_comp = aliased(EVMComponent)
            base_columns.append(pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'))
        else:
            base_columns.append(literal(None, String).label('cu_pink_paper_seal_no'))
        
        base_query = db.query(*base_columns).select_from(EVMComponent).filter(
            EVMComponent.component_type == EVMComponentType.DMM
        ).outerjoin(
            PairingRecord, PairingRecord.id == EVMComponent.pairing_id
        ).outerjoin(
            cu_comp, 
            and_(
                cu_comp.pairing_id == PairingRecord.id,
                cu_comp.component_type == EVMComponentType.CU
            )
        ).outerjoin(
            User, User.id == func.coalesce(cu_comp.last_received_from_id, EVMComponent.last_received_from_id)
        ).outerjoin(
            Warehouse, Warehouse.id == func.coalesce(cu_comp.current_warehouse_id, EVMComponent.current_warehouse_id)
        )
        
        if needs_flc:
            base_query = base_query.outerjoin(
                latest_flc, latest_flc.c.cu_id == cu_comp.id
            ).outerjoin(
                FLCRecord, 
                and_(
                    FLCRecord.cu_id == cu_comp.id,
                    FLCRecord.flc_date == latest_flc.c.latest_flc_date
                )
            )
        
        if needs_dmm_seal:
            base_query = base_query.outerjoin(
                dmm_seal_comp,
                and_(
                    dmm_seal_comp.pairing_id == PairingRecord.id,
                    dmm_seal_comp.component_type == EVMComponentType.DMM_SEAL
                )
            )
        
        if needs_pink_seal:
            base_query = base_query.outerjoin(
                pink_seal_comp,
                and_(
                    pink_seal_comp.pairing_id == PairingRecord.id,
                    pink_seal_comp.component_type == EVMComponentType.PINK_PAPER_SEAL
                )
            )
        
        dmm_seal_comp_ref = dmm_seal_comp if needs_dmm_seal else None
        pink_seal_comp_ref = pink_seal_comp if needs_pink_seal else None
        
        base_query = _apply_filters(base_query, filters, cu_comp, EVMComponent, dmm_seal_comp_ref, pink_seal_comp_ref)
        
        count_query = db.query(func.count(EVMComponent.id)).select_from(EVMComponent).filter(
            EVMComponent.component_type == EVMComponentType.DMM
        )
        
        if filters:
            count_query = count_query.outerjoin(PairingRecord, PairingRecord.id == EVMComponent.pairing_id)
            count_query = count_query.outerjoin(cu_comp, and_(cu_comp.pairing_id == PairingRecord.id, cu_comp.component_type == EVMComponentType.CU))
            count_query = count_query.outerjoin(User, User.id == func.coalesce(cu_comp.last_received_from_id, EVMComponent.last_received_from_id))
            count_query = count_query.outerjoin(Warehouse, Warehouse.id == func.coalesce(cu_comp.current_warehouse_id, EVMComponent.current_warehouse_id))
            
            if needs_flc:
                count_query = count_query.outerjoin(latest_flc, latest_flc.c.cu_id == cu_comp.id)
                count_query = count_query.outerjoin(FLCRecord, and_(FLCRecord.cu_id == cu_comp.id, FLCRecord.flc_date == latest_flc.c.latest_flc_date))
            
            if needs_dmm_seal:
                count_query = count_query.outerjoin(dmm_seal_comp, and_(dmm_seal_comp.pairing_id == PairingRecord.id, dmm_seal_comp.component_type == EVMComponentType.DMM_SEAL))
            
            if needs_pink_seal:
                count_query = count_query.outerjoin(pink_seal_comp, and_(pink_seal_comp.pairing_id == PairingRecord.id, pink_seal_comp.component_type == EVMComponentType.PINK_PAPER_SEAL))
            
            count_query = _apply_filters(count_query, filters, cu_comp, EVMComponent, dmm_seal_comp_ref, pink_seal_comp_ref)
        
        total_count = count_query.scalar() or 0
        
        if cursor:
            try:
                cursor_id = int(cursor)
                if direction == "next":
                    base_query = base_query.filter(EVMComponent.id > cursor_id)
                else:
                    base_query = base_query.filter(EVMComponent.id < cursor_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid cursor")
        
        if direction == "prev":
            base_query = base_query.order_by(EVMComponent.id.desc())
        else:
            base_query = base_query.order_by(EVMComponent.id.asc())
        
        results = base_query.limit(limit + 1).all()
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]
        
        if direction == "prev":
            results = results[::-1]
        
        formatted_results = []
        for idx, row in enumerate(results, 1):
            flc_status = ""
            if hasattr(row, 'flc_status') and row.flc_status is not None:
                flc_status = "Passed" if row.flc_status else "Failed"
            
            formatted_results.append({
                'sl_no': idx,
                'cu_dmm_received': row.cu_dmm_received or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'control_unit_no': row.control_unit_no or "",
                'month_year_manufacture_cu': row.cu_manufacture_date or "",
                'dmm_no': row.dmm_no or "",
                'month_year_manufacture_dmm': row.dmm_manufacture_date or "",
                'dmm_seal_no': getattr(row, 'dmm_seal_no', "") or "",
                'cu_pink_paper_seal_no': getattr(row, 'cu_pink_paper_seal_no', "") or "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if hasattr(row, 'flc_date') and row.flc_date else "",
                'flc_status': flc_status,
                'cu_box_no': str(row.cu_box_no) if row.cu_box_no else "",
                'cu_warehouse': row.cu_warehouse or "",
                'present_status_dmm': row.present_status_dmm or "",
                'present_status_cu': row.present_status_cu or ""
            })
        
        next_cursor = str(results[-1].id) if results and has_more and direction == "next" else None
        prev_cursor = str(results[0].id) if results and cursor and direction == "next" else None
        
        return MSRResponse(
            data=formatted_results,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more=has_more,
            total_count=total_count,
            first_serial=1 if formatted_results else None,
            last_serial=len(formatted_results) if formatted_results else None
        )
    except Exception as e:
        print(f"Regular query error: {str(e)}")
        raise

def _needs_flc_join(filters):
    if not filters:
        return False
    return any([
        filters.flc_date,
        filters.flc_date_start,
        filters.flc_date_end,
        filters.flc_status and filters.flc_status != "Failed"
    ])

def _apply_filters(query, filters, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp):
    if not filters:
        return query
    
    filter_conditions = []
    
    if filters.cu_dmm_received:
        filter_conditions.append(User.username.ilike(f"%{filters.cu_dmm_received}%"))
    
    if filters.date_of_receipt:
        filter_conditions.append(func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt) == filters.date_of_receipt)
    if filters.date_of_receipt_start:
        filter_conditions.append(func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt) >= filters.date_of_receipt_start)
    if filters.date_of_receipt_end:
        filter_conditions.append(func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt) <= filters.date_of_receipt_end)
    
    if filters.control_unit_no:
        filter_conditions.append(cu_comp.serial_number.ilike(f"%{filters.control_unit_no}%"))
    if filters.cu_manufacture_date:
        filter_conditions.append(cu_comp.dom.ilike(f"%{filters.cu_manufacture_date}%"))
    if filters.dmm_no:
        filter_conditions.append(dmm_comp.serial_number.ilike(f"%{filters.dmm_no}%"))
    if filters.dmm_manufacture_date:
        filter_conditions.append(dmm_comp.dom.ilike(f"%{filters.dmm_manufacture_date}%"))
    if filters.cu_box_no:
        filter_conditions.append(cu_comp.box_no.ilike(f"%{filters.cu_box_no}%"))
    if filters.cu_warehouse:
        filter_conditions.append(Warehouse.name.ilike(f"%{filters.cu_warehouse}%"))
    if filters.present_status_dmm:
        filter_conditions.append(dmm_comp.status.ilike(f"%{filters.present_status_dmm}%"))
    if filters.present_status_cu:
        filter_conditions.append(cu_comp.status.ilike(f"%{filters.present_status_cu}%"))
    
    if filters.dmm_seal_no and dmm_seal_comp:
        filter_conditions.append(dmm_seal_comp.serial_number.ilike(f"%{filters.dmm_seal_no}%"))
    if filters.cu_pink_paper_seal_no and pink_seal_comp:
        filter_conditions.append(pink_seal_comp.serial_number.ilike(f"%{filters.cu_pink_paper_seal_no}%"))
    
    if filters.flc_date:
        filter_conditions.append(func.date(FLCRecord.flc_date) == filters.flc_date)
    if filters.flc_date_start:
        filter_conditions.append(func.date(FLCRecord.flc_date) >= filters.flc_date_start)
    if filters.flc_date_end:
        filter_conditions.append(func.date(FLCRecord.flc_date) <= filters.flc_date_end)
    
    if filters.flc_status:
        if filters.flc_status == "Passed":
            filter_conditions.append(FLCRecord.passed == True)
        elif filters.flc_status == "Pending":
            filter_conditions.append(FLCRecord.passed.is_(None))
    
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query

def _apply_failed_cu_filters(query, filters):
    if not filters:
        return query
    
    filter_conditions = []
    
    if filters.cu_dmm_received:
        filter_conditions.append(User.username.ilike(f"%{filters.cu_dmm_received}%"))
    if filters.date_of_receipt:
        filter_conditions.append(EVMComponent.date_of_receipt == filters.date_of_receipt)
    if filters.date_of_receipt_start:
        filter_conditions.append(EVMComponent.date_of_receipt >= filters.date_of_receipt_start)
    if filters.date_of_receipt_end:
        filter_conditions.append(EVMComponent.date_of_receipt <= filters.date_of_receipt_end)
    if filters.control_unit_no:
        filter_conditions.append(EVMComponent.serial_number.ilike(f"%{filters.control_unit_no}%"))
    if filters.cu_manufacture_date:
        filter_conditions.append(EVMComponent.dom.ilike(f"%{filters.cu_manufacture_date}%"))
    if filters.cu_box_no:
        filter_conditions.append(EVMComponent.box_no.ilike(f"%{filters.cu_box_no}%"))
    if filters.cu_warehouse:
        filter_conditions.append(Warehouse.name.ilike(f"%{filters.cu_warehouse}%"))
    if filters.present_status_cu:
        filter_conditions.append(EVMComponent.status.ilike(f"%{filters.present_status_cu}%"))
    if filters.flc_date:
        filter_conditions.append(func.date(FLCRecord.flc_date) == filters.flc_date)
    if filters.flc_date_start:
        filter_conditions.append(func.date(FLCRecord.flc_date) >= filters.flc_date_start)
    if filters.flc_date_end:
        filter_conditions.append(func.date(FLCRecord.flc_date) <= filters.flc_date_end)
    
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query

def _build_bu_base_query(db):
    """Build the base query for BU without filters"""
    latest_flc_subquery = db.query(
        FLCBallotUnit.bu_id,
        func.max(FLCBallotUnit.flc_date).label('latest_flc_date')
    ).group_by(FLCBallotUnit.bu_id).subquery()
    
    query = db.query(
        EVMComponent.id,
        User.username.label('bu_received_from'),
        EVMComponent.date_of_receipt,
        EVMComponent.serial_number.label('ballot_unit_no'),
        EVMComponent.dom.label('year_of_manufacture'),
        FLCBallotUnit.flc_date,
        FLCBallotUnit.passed.label('flc_status'),
        EVMComponent.box_no.label('bu_box_no'),
        Warehouse.name.label('bu_warehouse')
    ).select_from(EVMComponent).filter(
        EVMComponent.component_type == EVMComponentType.BU
    ).outerjoin(
        User, 
        User.id == EVMComponent.last_received_from_id
    ).outerjoin(
        latest_flc_subquery, 
        latest_flc_subquery.c.bu_id == EVMComponent.id
    ).outerjoin(
        FLCBallotUnit, 
        and_(
            FLCBallotUnit.bu_id == EVMComponent.id,
            FLCBallotUnit.flc_date == latest_flc_subquery.c.latest_flc_date
        )
    ).outerjoin(
        Warehouse, 
        Warehouse.id == EVMComponent.current_warehouse_id
    )
    
    return query

def _apply_bu_filters(query, filters):
    """Apply filters to BU query"""
    if not filters:
        return query
    
    filter_conditions = []
    
    if filters.bu_received_from:
        filter_conditions.append(User.username.ilike(f"%{filters.bu_received_from}%"))
    
    # Date of receipt filters
    if filters.date_of_receipt:
        filter_conditions.append(EVMComponent.date_of_receipt == filters.date_of_receipt)
    if filters.date_of_receipt_start:
        filter_conditions.append(EVMComponent.date_of_receipt >= filters.date_of_receipt_start)
    if filters.date_of_receipt_end:
        filter_conditions.append(EVMComponent.date_of_receipt <= filters.date_of_receipt_end)
    
    if filters.ballot_unit_no:
        filter_conditions.append(EVMComponent.serial_number.ilike(f"%{filters.ballot_unit_no}%"))
    
    if filters.year_of_manufacture:
        filter_conditions.append(EVMComponent.dom.ilike(f"%{filters.year_of_manufacture}%"))
    
    # FLC date filters
    if filters.flc_date:
        filter_conditions.append(FLCBallotUnit.flc_date.cast(Date) == filters.flc_date)
    if filters.flc_date_start:
        filter_conditions.append(FLCBallotUnit.flc_date.cast(Date) >= filters.flc_date_start)
    if filters.flc_date_end:
        filter_conditions.append(FLCBallotUnit.flc_date.cast(Date) <= filters.flc_date_end)
    
    if filters.flc_status:
        if filters.flc_status == "Passed":
            filter_conditions.append(FLCBallotUnit.passed == True)
        elif filters.flc_status == "Failed":
            filter_conditions.append(FLCBallotUnit.passed == False)
        elif filters.flc_status == "Pending":
            filter_conditions.append(FLCBallotUnit.passed.is_(None))
    
    if filters.bu_box_no:
        filter_conditions.append(EVMComponent.box_no.ilike(f"%{filters.bu_box_no}%"))
    
    if filters.bu_warehouse:
        filter_conditions.append(Warehouse.name.ilike(f"%{filters.bu_warehouse}%"))
    
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query

def _get_bu_total_count(db, filters):
    """Get total count with optimized count query"""
    try:
        # Build optimized count query
        count_query = db.query(func.count(EVMComponent.id)).select_from(EVMComponent).filter(
            EVMComponent.component_type == EVMComponentType.BU
        ).outerjoin(
            User, 
            User.id == EVMComponent.last_received_from_id
        ).outerjoin(
            Warehouse, 
            Warehouse.id == EVMComponent.current_warehouse_id
        )
        
        # Add FLC joins only if FLC filters are applied
        if (filters and (filters.flc_date or filters.flc_date_start or filters.flc_date_end or filters.flc_status)):
            latest_flc_subquery = db.query(
                FLCBallotUnit.bu_id,
                func.max(FLCBallotUnit.flc_date).label('latest_flc_date')
            ).group_by(FLCBallotUnit.bu_id).subquery()
            
            count_query = count_query.outerjoin(
                latest_flc_subquery, 
                latest_flc_subquery.c.bu_id == EVMComponent.id
            ).outerjoin(
                FLCBallotUnit, 
                and_(
                    FLCBallotUnit.bu_id == EVMComponent.id,
                    FLCBallotUnit.flc_date == latest_flc_subquery.c.latest_flc_date
                )
            )
        
        count_query = _apply_bu_filters(count_query, filters)
        
        return count_query.scalar() or 0
        
    except Exception as e:
        print(f"Error in BU count query: {str(e)}")
        return 0

def MSR_BU_PAGINATED(
    limit: int = Query(default=500, le=1000, ge=1),
    cursor: Optional[str] = Query(default=None),
    direction: str = Query(default="next", regex="^(next|prev)$"),
    filters: MSRBUFilters = None
):
    """
    Fetch BU data in MSR Format with cursor pagination, serial numbers and filters
    """
    
    with Database.get_session() as db:
        try:
            # Get total count first (optimized separate query)
            total_count = _get_bu_total_count(db, filters)
            
            # Build main query
            base_query = _build_bu_base_query(db)
            
            # Apply filters
            filtered_query = _apply_bu_filters(base_query, filters)
            
            # Create a subquery with row numbers
            numbered_subquery = filtered_query.add_columns(
                func.row_number().over(order_by=EVMComponent.id.asc()).label('sl_no')
            ).subquery()
            
            # Main query from numbered subquery
            query = db.query(numbered_subquery)
            
            # Apply cursor pagination
            if cursor:
                try:
                    cursor_id = int(cursor)
                    if direction == "next":
                        query = query.filter(numbered_subquery.c.id > cursor_id)
                    else:  # prev
                        query = query.filter(numbered_subquery.c.id < cursor_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid cursor format")
            
            # Order and limit
            if direction == "prev":
                query = query.order_by(numbered_subquery.c.id.desc())
            else:
                query = query.order_by(numbered_subquery.c.id.asc())
            
            # Fetch limit + 1 to check if there are more records
            results = query.limit(limit + 1).all()
            
            # Check if there are more records
            has_more = len(results) > limit
            if has_more:
                results = results[:limit]
            
            # For prev direction, reverse the results to maintain proper order
            if direction == "prev":
                results = results[::-1]
            
            # Format results
            formatted_results = []
            first_serial = None
            last_serial = None
            
            for row in results:
                if first_serial is None:
                    first_serial = row.sl_no
                last_serial = row.sl_no
                
                formatted_row = {
                    'sl_no': row.sl_no,
                    'bu_received_from': row.bu_received_from or "",
                    'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                    'ballot_unit_no': row.ballot_unit_no or "",
                    'year_of_manufacture': row.year_of_manufacture if row.year_of_manufacture else "",
                    'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                    'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                    'bu_box_no': str(row.bu_box_no) if row.bu_box_no else "",
                    'bu_warehouse': row.bu_warehouse or ""
                }
                formatted_results.append(formatted_row)
            
            # Generate cursors
            next_cursor = None
            prev_cursor = None
            
            if formatted_results:
                last_id = results[-1].id if results else None
                first_id = results[0].id if results else None
                
                if has_more and direction == "next":
                    next_cursor = str(last_id)
                elif has_more and direction == "prev":
                    prev_cursor = str(first_id)
                
                if cursor and direction == "next":
                    prev_cursor = str(first_id)
                elif cursor and direction == "prev":
                    next_cursor = str(last_id)
            
            return MSRBUResponse(
                data=formatted_results,
                next_cursor=next_cursor,
                prev_cursor=prev_cursor,
                has_more=has_more,
                total_count=total_count,
                first_serial=first_serial,
                last_serial=last_serial
            )
            
        except Exception as e:
            print(f"Error in MSR_BU_PAGINATED: {str(e)}")
            raise
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
    flc_status: Optional[str] = None  # "Passed", "Failed", "Pending"
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

def _build_cu_dmm_base_query(db):
    """Build the base query for CU/DMM without filters"""
    cu_comp = aliased(EVMComponent, name='cu')
    dmm_comp = aliased(EVMComponent, name='dmm') 
    dmm_seal_comp = aliased(EVMComponent, name='dmm_seal')
    pink_seal_comp = aliased(EVMComponent, name='pink_seal')
    
    latest_flc_subquery = db.query(
        FLCRecord.cu_id,
        func.max(FLCRecord.flc_date).label('latest_flc_date')
    ).group_by(FLCRecord.cu_id).subquery()
    
    query = db.query(
        dmm_comp.id.label('dmm_id'),
        User.username.label('cu_dmm_received'),
        func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt).label('date_of_receipt'),
        cu_comp.serial_number.label('control_unit_no'),
        cu_comp.dom.label('cu_manufacture_date'),
        cu_comp.box_no.label('cu_box_no'),
        cu_comp.status.label('present_status_cu'),
        dmm_comp.serial_number.label('dmm_no'),
        dmm_comp.dom.label('dmm_manufacture_date'),
        dmm_comp.status.label('present_status_dmm'),
        dmm_seal_comp.serial_number.label('dmm_seal_no'),
        pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'),
        FLCRecord.flc_date,
        FLCRecord.passed.label('flc_status'),
        Warehouse.name.label('cu_warehouse')
    ).select_from(dmm_comp).filter(
        dmm_comp.component_type == EVMComponentType.DMM
    ).outerjoin(
        PairingRecord,
        PairingRecord.id == dmm_comp.pairing_id
    ).outerjoin(
        cu_comp, 
        and_(
            cu_comp.pairing_id == PairingRecord.id,
            cu_comp.component_type == EVMComponentType.CU
        )
    ).outerjoin(
        latest_flc_subquery, 
        latest_flc_subquery.c.cu_id == cu_comp.id
    ).outerjoin(
        FLCRecord, 
        and_(
            FLCRecord.cu_id == cu_comp.id,
            FLCRecord.flc_date == latest_flc_subquery.c.latest_flc_date
        )
    ).outerjoin(
        dmm_seal_comp, 
        and_(
            dmm_seal_comp.pairing_id == PairingRecord.id,
            dmm_seal_comp.component_type == EVMComponentType.DMM_SEAL
        )
    ).outerjoin(
        pink_seal_comp, 
        and_(
            pink_seal_comp.pairing_id == PairingRecord.id,
            pink_seal_comp.component_type == EVMComponentType.PINK_PAPER_SEAL
        )
    ).outerjoin(
        Warehouse, 
        Warehouse.id == func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id)
    ).outerjoin(
        User, 
        User.id == func.coalesce(cu_comp.last_received_from_id, dmm_comp.last_received_from_id)
    )
    
    return query, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp

def _apply_cu_dmm_filters(query, filters, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp):
    """Apply filters to CU/DMM query"""
    if not filters:
        return query
    
    filter_conditions = []
    
    if filters.cu_dmm_received:
        filter_conditions.append(User.username.ilike(f"%{filters.cu_dmm_received}%"))
    
    # Date of receipt filters
    if filters.date_of_receipt:
        filter_conditions.append(
            func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt) == filters.date_of_receipt
        )
    if filters.date_of_receipt_start:
        filter_conditions.append(
            func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt) >= filters.date_of_receipt_start
        )
    if filters.date_of_receipt_end:
        filter_conditions.append(
            func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt) <= filters.date_of_receipt_end
        )
    
    if filters.control_unit_no:
        filter_conditions.append(cu_comp.serial_number.ilike(f"%{filters.control_unit_no}%"))
    
    if filters.cu_manufacture_date:
        filter_conditions.append(cu_comp.dom.ilike(f"%{filters.cu_manufacture_date}%"))
    
    if filters.dmm_no:
        filter_conditions.append(dmm_comp.serial_number.ilike(f"%{filters.dmm_no}%"))
    
    if filters.dmm_manufacture_date:
        filter_conditions.append(dmm_comp.dom.ilike(f"%{filters.dmm_manufacture_date}%"))
    
    if filters.dmm_seal_no:
        filter_conditions.append(dmm_seal_comp.serial_number.ilike(f"%{filters.dmm_seal_no}%"))
    
    if filters.cu_pink_paper_seal_no:
        filter_conditions.append(pink_seal_comp.serial_number.ilike(f"%{filters.cu_pink_paper_seal_no}%"))
    
    # FLC date filters
    if filters.flc_date:
        filter_conditions.append(FLCRecord.flc_date.cast(Date) == filters.flc_date)
    if filters.flc_date_start:
        filter_conditions.append(FLCRecord.flc_date.cast(Date) >= filters.flc_date_start)
    if filters.flc_date_end:
        filter_conditions.append(FLCRecord.flc_date.cast(Date) <= filters.flc_date_end)
    
    if filters.flc_status:
        if filters.flc_status == "Passed":
            filter_conditions.append(FLCRecord.passed == True)
        elif filters.flc_status == "Failed":
            filter_conditions.append(FLCRecord.passed == False)
        elif filters.flc_status == "Pending":
            filter_conditions.append(FLCRecord.passed.is_(None))
    
    if filters.cu_box_no:
        filter_conditions.append(cu_comp.box_no.ilike(f"%{filters.cu_box_no}%"))
    
    if filters.cu_warehouse:
        filter_conditions.append(Warehouse.name.ilike(f"%{filters.cu_warehouse}%"))
    
    if filters.present_status_dmm:
        filter_conditions.append(dmm_comp.status.ilike(f"%{filters.present_status_dmm}%"))
    
    if filters.present_status_cu:
        filter_conditions.append(cu_comp.status.ilike(f"%{filters.present_status_cu}%"))
    
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query

def _get_cu_dmm_total_count(db, filters):
    """Get total count with optimized count query"""
    try:
        base_query, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp = _build_cu_dmm_base_query(db)
        
        # Build count query - only select what's needed for counting
        count_query = db.query(func.count(dmm_comp.id)).select_from(dmm_comp).filter(
            dmm_comp.component_type == EVMComponentType.DMM
        ).outerjoin(
            PairingRecord,
            PairingRecord.id == dmm_comp.pairing_id
        ).outerjoin(
            cu_comp, 
            and_(
                cu_comp.pairing_id == PairingRecord.id,
                cu_comp.component_type == EVMComponentType.CU
            )
        ).outerjoin(
            User, 
            User.id == func.coalesce(cu_comp.last_received_from_id, dmm_comp.last_received_from_id)
        ).outerjoin(
            Warehouse, 
            Warehouse.id == func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id)
        )
        
        # Add FLC joins only if FLC filters are applied
        if (filters and (filters.flc_date or filters.flc_date_start or filters.flc_date_end or filters.flc_status)):
            latest_flc_subquery = db.query(
                FLCRecord.cu_id,
                func.max(FLCRecord.flc_date).label('latest_flc_date')
            ).group_by(FLCRecord.cu_id).subquery()
            
            count_query = count_query.outerjoin(
                latest_flc_subquery, 
                latest_flc_subquery.c.cu_id == cu_comp.id
            ).outerjoin(
                FLCRecord, 
                and_(
                    FLCRecord.cu_id == cu_comp.id,
                    FLCRecord.flc_date == latest_flc_subquery.c.latest_flc_date
                )
            )
        
        # Add seal joins only if seal filters are applied
        if (filters and (filters.dmm_seal_no or filters.cu_pink_paper_seal_no)):
            if filters.dmm_seal_no:
                count_query = count_query.outerjoin(
                    dmm_seal_comp, 
                    and_(
                        dmm_seal_comp.pairing_id == PairingRecord.id,
                        dmm_seal_comp.component_type == EVMComponentType.DMM_SEAL
                    )
                )
            if filters.cu_pink_paper_seal_no:
                count_query = count_query.outerjoin(
                    pink_seal_comp, 
                    and_(
                        pink_seal_comp.pairing_id == PairingRecord.id,
                        pink_seal_comp.component_type == EVMComponentType.PINK_PAPER_SEAL
                    )
                )
        
        count_query = _apply_cu_dmm_filters(count_query, filters, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp)
        
        return count_query.scalar() or 0
        
    except Exception as e:
        print(f"Error in count query: {str(e)}")
        return 0

def MSR_CU_DMM_PAGINATED(
    limit: int = Query(default=500, le=1000, ge=1),
    cursor: Optional[str] = Query(default=None),
    direction: str = Query(default="next", regex="^(next|prev)$"),
    filters: MSRFilters = None
):
    """
    Fetch CU,DMM data in MSR Format with cursor pagination, serial numbers and filters
    """
    
    with Database.get_session() as db:
        try:
            # Get total count first (optimized separate query)
            total_count = _get_cu_dmm_total_count(db, filters)
            
            # Build main query with window function for serial numbers
            base_query, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp = _build_cu_dmm_base_query(db)
            
            # Apply filters
            filtered_query = _apply_cu_dmm_filters(base_query, filters, cu_comp, dmm_comp, dmm_seal_comp, pink_seal_comp)
            
            # Create a subquery with row numbers
            numbered_subquery = filtered_query.add_columns(
                func.row_number().over(order_by=dmm_comp.id.asc()).label('sl_no')
            ).subquery()
            
            # Main query from numbered subquery
            query = db.query(numbered_subquery)
            
            # Apply cursor pagination
            if cursor:
                try:
                    cursor_id = int(cursor)
                    if direction == "next":
                        query = query.filter(numbered_subquery.c.dmm_id > cursor_id)
                    else:  # prev
                        query = query.filter(numbered_subquery.c.dmm_id < cursor_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid cursor format")
            
            # Order and limit
            if direction == "prev":
                query = query.order_by(numbered_subquery.c.dmm_id.desc())
            else:
                query = query.order_by(numbered_subquery.c.dmm_id.asc())
            
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
                    'cu_dmm_received': row.cu_dmm_received or "",
                    'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                    'control_unit_no': row.control_unit_no or "",
                    'month_year_manufacture_cu': row.cu_manufacture_date or "",
                    'dmm_no': row.dmm_no or "",
                    'month_year_manufacture_dmm': row.dmm_manufacture_date or "",
                    'dmm_seal_no': row.dmm_seal_no or "",
                    'cu_pink_paper_seal_no': row.cu_pink_paper_seal_no or "",
                    'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                    'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                    'cu_box_no': str(row.cu_box_no) if row.cu_box_no else "",
                    'cu_warehouse': row.cu_warehouse or "",
                    'present_status_dmm': row.present_status_dmm or "",
                    'present_status_cu': row.present_status_cu or ""
                }
                formatted_results.append(formatted_row)
            
            # Generate cursors
            next_cursor = None
            prev_cursor = None
            
            if formatted_results:
                last_dmm_id = results[-1].dmm_id if results else None
                first_dmm_id = results[0].dmm_id if results else None
                
                if has_more and direction == "next":
                    next_cursor = str(last_dmm_id)
                elif has_more and direction == "prev":
                    prev_cursor = str(first_dmm_id)
                
                if cursor and direction == "next":
                    prev_cursor = str(first_dmm_id)
                elif cursor and direction == "prev":
                    next_cursor = str(last_dmm_id)
            
            return MSRResponse(
                data=formatted_results,
                next_cursor=next_cursor,
                prev_cursor=prev_cursor,
                has_more=has_more,
                total_count=total_count,
                first_serial=first_serial,
                last_serial=last_serial
            )
            
        except Exception as e:
            print(f"Error in MSR_CU_DMM_PAGINATED: {str(e)}")
            raise

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
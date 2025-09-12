from typing import Optional, List
from fastapi import Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date
from sqlalchemy import and_, or_, func, text, Date, case, exists,Integer
from sqlalchemy.orm import aliased
from core.db import Database
from models.evm import EVMComponent, EVMComponentType, PairingRecord, FLCRecord
from models.users import User, Warehouse, District
from models.users import User, Warehouse
from typing import Optional, List
from fastapi import Query, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, date
from sqlalchemy import and_, or_, func, text, Date,union_all
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
    cu_box_no_start: Optional[str] = None
    cu_box_no_end: Optional[str] = None
    cu_warehouse: Optional[str] = None
    present_status_dmm: Optional[str] = None
    present_status_cu: Optional[str] = None

class MSRResponse(BaseModel):
    data: List[dict]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more_next: bool = False
    has_more_prev: bool = False
    total_count: int = 0
    first_serial: Optional[int] = None
    last_serial: Optional[int] = None
    current_page: int = 1
    total_pages: int = 0

def MSR_CU_DMM_PAGINATED(
    limit: int = Query(default=25, le=100, ge=1),
    cursor: Optional[str] = Query(default=None),
    direction: str = Query(default="next", regex="^(next|prev)$"),
    filters: MSRFilters = None
):
    with Database.get_session() as db:
        try:
            # Handle failed CU filter with special logic
            is_failed_cu_filter = filters and filters.flc_status == "Failed"
            
            if is_failed_cu_filter:
                return _handle_failed_cu_query(db, limit, cursor, direction, filters)
            else:
                return _handle_unified_query(db, limit, cursor, direction, filters)
                
        except Exception as e:
            print(f"MSR query error: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail="Query failed")

def _handle_failed_cu_query(db, limit, cursor, direction, filters):
    """Handle the special case for failed CU components"""
    try:
        # Get latest FLC records for each CU
        latest_flc = db.query(
            FLCRecord.cu_id,
            func.max(FLCRecord.flc_date).label('latest_flc_date')
        ).group_by(FLCRecord.cu_id).subquery()
        
        # Base query for failed CUs
        base_query = db.query(
            EVMComponent.id,
            User.username.label('cu_dmm_received'),
            EVMComponent.date_of_receipt,
            EVMComponent.serial_number.label('control_unit_no'),
            EVMComponent.dom.label('cu_manufacture_date'),
            EVMComponent.box_no.label('cu_box_no'),
            EVMComponent.status.label('present_status_cu'),
            FLCRecord.flc_date,
            Warehouse.name.label('cu_warehouse'),
            District.name.label('district'),
            literal("").label('dmm_no'),
            literal("").label('dmm_manufacture_date'),
            literal("").label('present_status_dmm'),
            literal("").label('dmm_seal_no'),
            literal("").label('cu_pink_paper_seal_no')
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
            User, User.id == EVMComponent.current_user_id
        ).outerjoin(
            Warehouse, Warehouse.id == EVMComponent.current_warehouse_id
        ).outerjoin(
            District, District.id == User.district_id
        ).filter(
            EVMComponent.component_type == EVMComponentType.CU
        )
        
        # Apply filters
        base_query = _apply_failed_cu_filters(base_query, filters)
        
        # Get total count
        total_count = base_query.count()
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
        
        # Get cursor position for pagination calculation
        cursor_position = 0
        if cursor:
            try:
                cursor_id = int(cursor)
                # Get position of cursor in the ordered result set
                position_query = base_query.filter(EVMComponent.id < cursor_id).count()
                if direction == "next":
                    cursor_position = position_query
                else:  # prev
                    cursor_position = position_query - limit + 1
                    if cursor_position < 0:
                        cursor_position = 0
            except ValueError:
                cursor_position = 0
        
        # Apply cursor-based pagination
        paginated_query, has_more_next, has_more_prev = _apply_cursor_pagination_with_info(
            base_query, cursor, direction, EVMComponent.id, limit, total_count
        )
        
        # Execute query
        results = paginated_query.limit(limit + 1).all()
        actual_has_more = len(results) > limit
        if actual_has_more:
            results = results[:limit]
        
        if direction == "prev":
            results = results[::-1]
        
        # Calculate serial numbers and page info
        current_page = (cursor_position // limit) + 1
        first_serial = cursor_position + 1
        last_serial = min(cursor_position + len(results), total_count)
        
        # Format results
        formatted_results = []
        for idx, row in enumerate(results):
            serial_no = first_serial + idx
            formatted_results.append({
                'sl_no': serial_no,
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
                'present_status_cu': row.present_status_cu or "",
                'district': row.district or ""
            })
        
        # Calculate cursors
        next_cursor = None
        prev_cursor = None
        
        if results:
            if has_more_next:
                next_cursor = str(results[-1].id)
            if has_more_prev:
                prev_cursor = str(results[0].id)
        
        return MSRResponse(
            data=formatted_results,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more_next=has_more_next,
            has_more_prev=has_more_prev,
            total_count=total_count,
            first_serial=first_serial if formatted_results else None,
            last_serial=last_serial if formatted_results else None,
            current_page=current_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        print(f"Failed CU query error: {str(e)}")
        raise

def _handle_unified_query(db, limit, cursor, direction, filters):
    """Handle unified query for both paired and unpaired components"""
    try:
        # Create aliases for different component types
        cu_comp = aliased(EVMComponent)
        dmm_comp = aliased(EVMComponent) 
        dmm_seal_comp = aliased(EVMComponent)
        pink_seal_comp = aliased(EVMComponent)
        cu_user = aliased(User)
        dmm_user = aliased(User)
        cu_district = aliased(District)
        dmm_district = aliased(District)
        cu_warehouse = aliased(Warehouse)
        dmm_warehouse = aliased(Warehouse)
        
        # Check if we need FLC joins
        needs_flc = _needs_flc_join(filters)
        needs_dmm_seal = filters and filters.dmm_seal_no
        needs_pink_seal = filters and filters.cu_pink_paper_seal_no
        
        # Subquery for latest FLC records if needed
        latest_flc = None
        if needs_flc:
            latest_flc = db.query(
                FLCRecord.cu_id,
                func.max(FLCRecord.flc_date).label('latest_flc_date')
            ).group_by(FLCRecord.cu_id).subquery()
        
        # Build the main query using UNION approach for better performance
        # Query 1: Paired components (DMM-based with CU data)
        paired_columns = [
            dmm_comp.id.label('primary_id'),
            literal(1).label('query_type'),  # 1 for paired
            func.coalesce(cu_user.username, dmm_user.username).label('cu_dmm_received'),
            func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt).label('date_of_receipt'),
            cu_comp.serial_number.label('control_unit_no'),
            cu_comp.dom.label('cu_manufacture_date'),
            dmm_comp.serial_number.label('dmm_no'),
            dmm_comp.dom.label('dmm_manufacture_date'),
            cu_comp.status.label('present_status_cu'),
            dmm_comp.status.label('present_status_dmm'),
            func.coalesce(cu_comp.box_no, dmm_comp.box_no).label('cu_box_no'),
            func.coalesce(cu_warehouse.name, dmm_warehouse.name).label('cu_warehouse'),
            func.coalesce(cu_district.name, dmm_district.name).label('district')
        ]
        
        # Add FLC columns
        if needs_flc:
            paired_columns.extend([
                FLCRecord.flc_date,
                FLCRecord.passed.label('flc_status')
            ])
        else:
            paired_columns.extend([
                literal(None, Date).label('flc_date'),
                literal(None).label('flc_status')
            ])
        
        # Add seal columns
        if needs_dmm_seal:
            paired_columns.append(dmm_seal_comp.serial_number.label('dmm_seal_no'))
        else:
            paired_columns.append(literal("").label('dmm_seal_no'))
            
        if needs_pink_seal:
            paired_columns.append(pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'))
        else:
            paired_columns.append(literal("").label('cu_pink_paper_seal_no'))
        
        # Build paired query
        paired_query = db.query(*paired_columns).select_from(dmm_comp).filter(
            and_(
                dmm_comp.component_type == EVMComponentType.DMM,
                dmm_comp.pairing_id.isnot(None)
            )
        ).outerjoin(
            PairingRecord, PairingRecord.id == dmm_comp.pairing_id
        ).outerjoin(
            cu_comp, 
            and_(
                cu_comp.pairing_id == PairingRecord.id,
                cu_comp.component_type == EVMComponentType.CU
            )
        ).outerjoin(
            cu_user, cu_user.id == cu_comp.current_user_id
        ).outerjoin(
            dmm_user, dmm_user.id == dmm_comp.current_user_id
        ).outerjoin(
            cu_district, cu_district.id == cu_user.district_id
        ).outerjoin(
            dmm_district, dmm_district.id == dmm_user.district_id
        ).outerjoin(
            cu_warehouse, cu_warehouse.id == cu_comp.current_warehouse_id
        ).outerjoin(
            dmm_warehouse, dmm_warehouse.id == dmm_comp.current_warehouse_id
        )
        
        # Add FLC joins if needed
        if needs_flc:
            paired_query = paired_query.outerjoin(
                latest_flc, latest_flc.c.cu_id == cu_comp.id
            ).outerjoin(
                FLCRecord,
                and_(
                    FLCRecord.cu_id == cu_comp.id,
                    FLCRecord.flc_date == latest_flc.c.latest_flc_date
                )
            )
        
        # Add seal joins if needed
        if needs_dmm_seal:
            paired_query = paired_query.outerjoin(
                dmm_seal_comp,
                and_(
                    dmm_seal_comp.pairing_id == PairingRecord.id,
                    dmm_seal_comp.component_type == EVMComponentType.DMM_SEAL
                )
            )
            
        if needs_pink_seal:
            paired_query = paired_query.outerjoin(
                pink_seal_comp,
                and_(
                    pink_seal_comp.pairing_id == PairingRecord.id,
                    pink_seal_comp.component_type == EVMComponentType.PINK_PAPER_SEAL
                )
            )
        
        # Query 2: Unpaired DMM components
        unpaired_dmm_columns = [
            dmm_comp.id.label('primary_id'),
            literal(2).label('query_type'),  # 2 for unpaired DMM
            dmm_user.username.label('cu_dmm_received'),
            dmm_comp.date_of_receipt,
            literal("").label('control_unit_no'),
            literal("").label('cu_manufacture_date'),
            dmm_comp.serial_number.label('dmm_no'),
            dmm_comp.dom.label('dmm_manufacture_date'),
            literal("").label('present_status_cu'),
            dmm_comp.status.label('present_status_dmm'),
            dmm_comp.box_no.label('cu_box_no'),
            dmm_warehouse.name.label('cu_warehouse'),
            dmm_district.name.label('district'),
            literal(None, Date).label('flc_date'),
            literal(None).label('flc_status'),
            literal("").label('dmm_seal_no'),
            literal("").label('cu_pink_paper_seal_no')
        ]
        
        unpaired_dmm_query = db.query(*unpaired_dmm_columns).select_from(dmm_comp).filter(
            and_(
                dmm_comp.component_type == EVMComponentType.DMM,
                dmm_comp.pairing_id.is_(None)
            )
        ).outerjoin(
            dmm_user, dmm_user.id == dmm_comp.current_user_id
        ).outerjoin(
            dmm_district, dmm_district.id == dmm_user.district_id
        ).outerjoin(
            dmm_warehouse, dmm_warehouse.id == dmm_comp.current_warehouse_id
        )
        
        # Query 3: Unpaired CU components
        unpaired_cu_columns = [
            cu_comp.id.label('primary_id'),
            literal(3).label('query_type'),  # 3 for unpaired CU
            cu_user.username.label('cu_dmm_received'),
            cu_comp.date_of_receipt,
            cu_comp.serial_number.label('control_unit_no'),
            cu_comp.dom.label('cu_manufacture_date'),
            literal("").label('dmm_no'),
            literal("").label('dmm_manufacture_date'),
            cu_comp.status.label('present_status_cu'),
            literal("").label('present_status_dmm'),
            cu_comp.box_no.label('cu_box_no'),
            cu_warehouse.name.label('cu_warehouse'),
            cu_district.name.label('district')
        ]
        
        # Add FLC data for unpaired CUs if needed
        if needs_flc:
            unpaired_cu_columns.extend([
                FLCRecord.flc_date,
                FLCRecord.passed.label('flc_status')
            ])
        else:
            unpaired_cu_columns.extend([
                literal(None, Date).label('flc_date'),
                literal(None).label('flc_status')
            ])
            
        unpaired_cu_columns.extend([
            literal("").label('dmm_seal_no'),
            literal("").label('cu_pink_paper_seal_no')
        ])
        
        unpaired_cu_query = db.query(*unpaired_cu_columns).select_from(cu_comp).filter(
            and_(
                cu_comp.component_type == EVMComponentType.CU,
                cu_comp.pairing_id.is_(None)
            )
        ).outerjoin(
            cu_user, cu_user.id == cu_comp.current_user_id
        ).outerjoin(
            cu_district, cu_district.id == cu_user.district_id
        ).outerjoin(
            cu_warehouse, cu_warehouse.id == cu_comp.current_warehouse_id
        )
        
        # Add FLC joins for unpaired CUs if needed
        if needs_flc:
            unpaired_cu_query = unpaired_cu_query.outerjoin(
                latest_flc, latest_flc.c.cu_id == cu_comp.id
            ).outerjoin(
                FLCRecord,
                and_(
                    FLCRecord.cu_id == cu_comp.id,
                    FLCRecord.flc_date == latest_flc.c.latest_flc_date
                )
            )
        
        # Combine all queries
        combined_query = union_all(paired_query, unpaired_dmm_query, unpaired_cu_query).alias('combined_results')
        
        # Create final query from combined results
        final_query = db.query(combined_query)
        
        # Apply filters to combined query
        final_query = _apply_unified_filters(final_query, filters, combined_query)
        
        # Get total count
        count_query = db.query(func.count()).select_from(combined_query)
        count_query = _apply_unified_filters(count_query, filters, combined_query)
        total_count = count_query.scalar() or 0
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
        
        # Get cursor position for pagination calculation
        cursor_position = 0
        if cursor:
            try:
                cursor_id = int(cursor)
                # Get position of cursor in the ordered result set
                position_query = db.query(func.count()).select_from(combined_query).filter(
                    combined_query.c.primary_id < cursor_id
                )
                position_query = _apply_unified_filters(position_query, filters, combined_query)
                position_count = position_query.scalar() or 0
                
                if direction == "next":
                    cursor_position = position_count
                else:  # prev
                    cursor_position = position_count - limit + 1
                    if cursor_position < 0:
                        cursor_position = 0
            except ValueError:
                cursor_position = 0
        
        # Apply cursor pagination - but don't use the has_more from this function yet
        paginated_query, _, _ = _apply_cursor_pagination_with_info(
            final_query, cursor, direction, combined_query.c.primary_id, limit, total_count
        )
        
        # Execute query with limit + 1 to check for more records
        results = paginated_query.limit(limit + 1).all()
        
        # Determine if there are more records
        has_more_next = False
        has_more_prev = False
        
        if len(results) > limit:
            results = results[:limit]  # Remove the extra record
            if direction == "next":
                has_more_next = True
            else:
                has_more_next = True  # There might be more in the next direction
        
        # Calculate has_more_prev and has_more_next based on current position
        if cursor_position > 0:
            has_more_prev = True
        
        if cursor_position + len(results) < total_count:
            has_more_next = True
        
        if direction == "prev":
            results = results[::-1]
        
        # Calculate serial numbers and page info
        current_page = (cursor_position // limit) + 1
        first_serial = cursor_position + 1
        last_serial = min(cursor_position + len(results), total_count)
        
        # Format results
        formatted_results = []
        for idx, row in enumerate(results):
            serial_no = first_serial + idx
            
            flc_status = ""
            if hasattr(row, 'flc_status') and row.flc_status is not None:
                flc_status = "Passed" if row.flc_status else "Failed"
            
            formatted_results.append({
                'sl_no': serial_no,
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
                'present_status_cu': row.present_status_cu or "",
                'district': row.district or ""
            })
        
        # Calculate cursors - only set if there are actually more records
        next_cursor = None
        prev_cursor = None
        
        if results and has_more_next:
            next_cursor = str(results[-1].primary_id)
        if results and has_more_prev:
            prev_cursor = str(results[0].primary_id)
        
        return MSRResponse(
            data=formatted_results,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more_next=has_more_next,
            has_more_prev=has_more_prev,
            total_count=total_count,
            first_serial=first_serial if formatted_results else None,
            last_serial=last_serial if formatted_results else None,
            current_page=current_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        print(f"Unified query error: {str(e)}")
        raise

def _needs_flc_join(filters):
    """Check if FLC joins are needed based on filters"""
    if not filters:
        return False
    return any([
        filters.flc_date,
        filters.flc_date_start,
        filters.flc_date_end,
        filters.flc_status and filters.flc_status != "Failed"
    ])

def _apply_cursor_pagination_with_info(query, cursor, direction, id_column, limit, total_count):
    """Apply cursor-based pagination and return has_more info"""
    has_more_next = False
    has_more_prev = False
    
    if cursor:
        try:
            cursor_id = int(cursor)
            if direction == "next":
                query = query.filter(id_column > cursor_id)
                has_more_prev = True  # If we have a cursor, there should be previous records
            else:  # prev
                query = query.filter(id_column < cursor_id)
                has_more_next = True  # If we have a cursor, there might be next records
        except ValueError:
            pass
    else:
        # First page - no previous records
        has_more_prev = False
    
    if direction == "prev":
        query = query.order_by(id_column.desc())
    else:
        query = query.order_by(id_column.asc())
    
    return query, has_more_next, has_more_prev

def _apply_unified_filters(query, filters, combined_table):
    """Apply filters to the unified query result"""
    if not filters:
        return query
    
    filter_conditions = []
    
    if filters.cu_dmm_received:
        filter_conditions.append(combined_table.c.cu_dmm_received.ilike(f"%{filters.cu_dmm_received}%"))
    
    if filters.date_of_receipt:
        filter_conditions.append(combined_table.c.date_of_receipt == filters.date_of_receipt)
    if filters.date_of_receipt_start:
        filter_conditions.append(combined_table.c.date_of_receipt >= filters.date_of_receipt_start)
    if filters.date_of_receipt_end:
        filter_conditions.append(combined_table.c.date_of_receipt <= filters.date_of_receipt_end)
    
    if filters.control_unit_no:
        filter_conditions.append(combined_table.c.control_unit_no.ilike(f"%{filters.control_unit_no}%"))
    if filters.cu_manufacture_date:
        filter_conditions.append(combined_table.c.cu_manufacture_date.ilike(f"%{filters.cu_manufacture_date}%"))
    if filters.dmm_no:
        filter_conditions.append(combined_table.c.dmm_no.ilike(f"%{filters.dmm_no}%"))
    if filters.dmm_manufacture_date:
        filter_conditions.append(combined_table.c.dmm_manufacture_date.ilike(f"%{filters.dmm_manufacture_date}%"))
    
    # Fix: Use cu_box_no_start and cu_box_no_end instead of cu_box_no
    if filters.cu_box_no_start or filters.cu_box_no_end:
        box_conditions = _apply_box_number_range_filter(
            filters.cu_box_no_start, filters.cu_box_no_end, combined_table.c.cu_box_no
        )
        if box_conditions:
            filter_conditions.extend(box_conditions)
    
    if filters.cu_warehouse:
        filter_conditions.append(combined_table.c.cu_warehouse.ilike(f"%{filters.cu_warehouse}%"))
    if filters.present_status_dmm:
        filter_conditions.append(combined_table.c.present_status_dmm.ilike(f"%{filters.present_status_dmm}%"))
    if filters.present_status_cu:
        filter_conditions.append(combined_table.c.present_status_cu.ilike(f"%{filters.present_status_cu}%"))
    
    if filters.dmm_seal_no:
        filter_conditions.append(combined_table.c.dmm_seal_no.ilike(f"%{filters.dmm_seal_no}%"))
    if filters.cu_pink_paper_seal_no:
        filter_conditions.append(combined_table.c.cu_pink_paper_seal_no.ilike(f"%{filters.cu_pink_paper_seal_no}%"))
    
    if filters.flc_date:
        filter_conditions.append(func.date(combined_table.c.flc_date) == filters.flc_date)
    if filters.flc_date_start:
        filter_conditions.append(func.date(combined_table.c.flc_date) >= filters.flc_date_start)
    if filters.flc_date_end:
        filter_conditions.append(func.date(combined_table.c.flc_date) <= filters.flc_date_end)
    
    if filters.flc_status:
        if filters.flc_status == "Passed":
            filter_conditions.append(combined_table.c.flc_status == True)
        elif filters.flc_status == "Pending":
            filter_conditions.append(combined_table.c.flc_status.is_(None))
    
    if filter_conditions:
        query = query.filter(and_(*filter_conditions))
    
    return query

def _apply_box_number_range_filter(cu_box_no_start, cu_box_no_end, cu_box_no_column):
    """Apply box number range filter for unified query"""
    box_conditions = []
    
    if cu_box_no_start:
        try:
            start_num = int(cu_box_no_start)
            box_conditions.append(func.cast(cu_box_no_column, Integer) >= start_num)
        except ValueError:
            # If not a number, treat as string comparison
            box_conditions.append(cu_box_no_column >= cu_box_no_start)
    
    if cu_box_no_end:
        try:
            end_num = int(cu_box_no_end)
            box_conditions.append(func.cast(cu_box_no_column, Integer) <= end_num)
        except ValueError:
            # If not a number, treat as string comparison
            box_conditions.append(cu_box_no_column <= cu_box_no_end)
    
    return box_conditions

def _apply_failed_cu_filters(query, filters):
    """Apply filters specific to failed CU query"""
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
    if filters.cu_box_no_start or filters.cu_box_no_end:
        box_conditions = _apply_box_number_range_filter(
            query, filters.cu_box_no_start, filters.cu_box_no_end, EVMComponent.box_no
        )
        filter_conditions.extend(box_conditions)
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
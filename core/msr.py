from sqlalchemy.orm import aliased, selectinload, joinedload
from sqlalchemy import and_, select, case, func
from datetime import datetime
from core.db import Database
from models.evm import EVMComponent, EVMComponentType, PairingRecord, FLCRecord, AllotmentItem, Allotment,FLCBallotUnit
from models.users import User, Warehouse

def get_evm_pairing_data():
    """
    Fetch CU,DMM data in MSR Format. Used by SEC
    """
    
    with Database.get_session() as db:
        # Create aliases for different component types
        cu_comp = aliased(EVMComponent, name='cu')
        dmm_comp = aliased(EVMComponent, name='dmm') 
        dmm_seal_comp = aliased(EVMComponent, name='dmm_seal')
        pink_seal_comp = aliased(EVMComponent, name='pink_seal')
        
        # Subquery to get the latest FLC record for each CU
        latest_flc_subquery = db.query(
            FLCRecord.cu_id,
            func.max(FLCRecord.flc_date).label('latest_flc_date')
        ).group_by(FLCRecord.cu_id).subquery()
        
        # Build highly optimized query with strategic column selection
        query = db.query(
            PairingRecord.id.label('pairing_id'),
            User.username.label('cu_dmm_received'),
            cu_comp.date_of_receipt,
            cu_comp.serial_number.label('control_unit_no'),
            cu_comp.dom.label('cu_manufacture_date'),
            cu_comp.box_no.label('cu_box_no'),
            cu_comp.status.label('present_status_cu'),
            cu_comp.current_warehouse_id,
            cu_comp.last_received_from_id,
            dmm_comp.serial_number.label('dmm_no'),
            dmm_comp.dom.label('dmm_manufacture_date'),
            dmm_comp.status.label('present_status_dmm'),
            dmm_seal_comp.serial_number.label('dmm_seal_no'),
            pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'),
            FLCRecord.flc_date,
            FLCRecord.passed.label('flc_status'),
            Warehouse.name.label('cu_warehouse')
        ).select_from(PairingRecord)
        
        # Optimize joins - use INNER JOIN where possible, LEFT JOIN only when needed
        query = query.join(
            cu_comp, 
            and_(
                cu_comp.pairing_id == PairingRecord.id,
                cu_comp.component_type == EVMComponentType.CU
            )
        ).outerjoin(
            dmm_comp, 
            and_(
                dmm_comp.pairing_id == PairingRecord.id,
                dmm_comp.component_type == EVMComponentType.DMM
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
            latest_flc_subquery, 
            latest_flc_subquery.c.cu_id == cu_comp.id
        ).outerjoin(
            FLCRecord, 
            and_(
                FLCRecord.cu_id == cu_comp.id,
                FLCRecord.flc_date == latest_flc_subquery.c.latest_flc_date
            )
        ).outerjoin(
            Warehouse, Warehouse.id == cu_comp.current_warehouse_id
        ).outerjoin(
            User, User.id == cu_comp.last_received_from_id
        )
        
        # Add ordering and execute
        results = query.order_by(PairingRecord.id).all()
        
        # Bulk format results using list comprehension for better performance
        return [
            {
                'sl_no': i,
                'cu_dmm_received': row.cu_dmm_received or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'control_unit_no': row.control_unit_no or "",
                'month_year_manufacture_cu': row.cu_manufacture_date.strftime("%m/%Y") if row.cu_manufacture_date else "",
                'dmm_no': row.dmm_no or "",
                'month_year_manufacture_dmm': row.dmm_manufacture_date.strftime("%m/%Y") if row.dmm_manufacture_date else "",
                'dmm_seal_no': row.dmm_seal_no or "",
                'cu_pink_paper_seal_no': row.cu_pink_paper_seal_no or "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                'cu_box_no': str(row.cu_box_no) if row.cu_box_no else "",
                'cu_warehouse': row.cu_warehouse or "",
                'present_status_dmm': row.present_status_dmm or "",
                'present_status_cu': row.present_status_cu or ""
            }
            for i, row in enumerate(results, 1)
        ]


def get_evm_pairing_data_by_user(user_id):
    """
    Fetch CU,DMM data for Components with a user in MSR Format
    """
    
    with Database.get_session() as db:
        # Create aliases for different component types
        cu_comp = aliased(EVMComponent, name='cu')
        dmm_comp = aliased(EVMComponent, name='dmm') 
        dmm_seal_comp = aliased(EVMComponent, name='dmm_seal')
        pink_seal_comp = aliased(EVMComponent, name='pink_seal')
        
        # Subquery to get the latest FLC record for each CU
        latest_flc_subquery = db.query(
            FLCRecord.cu_id,
            func.max(FLCRecord.flc_date).label('latest_flc_date')
        ).group_by(FLCRecord.cu_id).subquery()
        
        # Build optimized query filtered by user
        query = db.query(
            PairingRecord.id.label('pairing_id'),
            User.username.label('cu_dmm_received'),
            cu_comp.date_of_receipt,
            cu_comp.serial_number.label('control_unit_no'),
            cu_comp.dom.label('cu_manufacture_date'),
            cu_comp.box_no.label('cu_box_no'),
            cu_comp.status.label('present_status_cu'),
            cu_comp.current_warehouse_id,
            cu_comp.last_received_from_id,
            dmm_comp.serial_number.label('dmm_no'),
            dmm_comp.dom.label('dmm_manufacture_date'),
            dmm_comp.status.label('present_status_dmm'),
            dmm_seal_comp.serial_number.label('dmm_seal_no'),
            pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'),
            FLCRecord.flc_date,
            FLCRecord.passed.label('flc_status'),
            Warehouse.name.label('cu_warehouse')
        ).select_from(PairingRecord)
        
        # Join with CU component and filter by user
        query = query.join(
            cu_comp, 
            and_(
                cu_comp.pairing_id == PairingRecord.id,
                cu_comp.component_type == EVMComponentType.CU,
                cu_comp.current_user_id == user_id  # Filter by user
            )
        ).outerjoin(
            dmm_comp, 
            and_(
                dmm_comp.pairing_id == PairingRecord.id,
                dmm_comp.component_type == EVMComponentType.DMM
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
            latest_flc_subquery, 
            latest_flc_subquery.c.cu_id == cu_comp.id
        ).outerjoin(
            FLCRecord, 
            and_(
                FLCRecord.cu_id == cu_comp.id,
                FLCRecord.flc_date == latest_flc_subquery.c.latest_flc_date
            )
        ).outerjoin(
            Warehouse, Warehouse.id == cu_comp.current_warehouse_id
        ).outerjoin(
            User, User.id == cu_comp.current_user_id
        )
        
        # Execute query
        results = query.order_by(PairingRecord.id).all()
        
        # Format results
        return [
            {
                'sl_no': i,
                'cu_dmm_received': row.cu_dmm_received or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'control_unit_no': row.control_unit_no or "",
                'month_year_manufacture_cu': row.cu_manufacture_date.strftime("%m/%Y") if row.cu_manufacture_date else "",
                'dmm_no': row.dmm_no or "",
                'month_year_manufacture_dmm': row.dmm_manufacture_date.strftime("%m/%Y") if row.dmm_manufacture_date else "",
                'dmm_seal_no': row.dmm_seal_no or "",
                'cu_pink_paper_seal_no': row.cu_pink_paper_seal_no or "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                'cu_box_no': str(row.cu_box_no) if row.cu_box_no else "",
                'cu_warehouse': row.cu_warehouse or "",
                'present_status_dmm': row.present_status_dmm or "",
                'present_status_cu': row.present_status_cu or ""
            }
            for i, row in enumerate(results, 1)
        ]




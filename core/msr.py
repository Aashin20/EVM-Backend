from sqlalchemy.orm import aliased, selectinload, joinedload
from sqlalchemy import and_, select, case, func
from datetime import datetime
from core.db import Database
from models.evm import EVMComponent, EVMComponentType, PairingRecord, FLCRecord, AllotmentItem, Allotment,FLCBallotUnit
from models.users import User, Warehouse

from sqlalchemy import func, text

def MSR_CU_DMM():
    """
    Fetch CU,DMM data in MSR Format including unpaired DMMs. Used by SEC
    """
    
    with Database.get_session() as db:
        try:
            cu_comp = aliased(EVMComponent, name='cu')
            dmm_comp = aliased(EVMComponent, name='dmm') 
            dmm_seal_comp = aliased(EVMComponent, name='dmm_seal')
            pink_seal_comp = aliased(EVMComponent, name='pink_seal')
            
     
            latest_flc_subquery = db.query(
                FLCRecord.cu_id,
                func.max(FLCRecord.flc_date).label('latest_flc_date')
            ).group_by(FLCRecord.cu_id).subquery()
            
          
            query = db.query(
                PairingRecord.id.label('pairing_id'),
                User.username.label('cu_dmm_received'),
                func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt).label('date_of_receipt'),
                cu_comp.serial_number.label('control_unit_no'),
                cu_comp.dom.label('cu_manufacture_date'),
                cu_comp.box_no.label('cu_box_no'),
                cu_comp.status.label('present_status_cu'),
                func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id).label('current_warehouse_id'),
                func.coalesce(cu_comp.last_received_from_id, dmm_comp.last_received_from_id).label('last_received_from_id'),
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
            )
            
         
            query = query.outerjoin(
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
            
         
            results = query.order_by(
                PairingRecord.id.asc().nulls_last(),
                dmm_comp.id.asc()
            ).all()
            
          
            formatted_results = []
            
            for i, row in enumerate(results, 1):
                formatted_row = {
                    'sl_no': i,
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
            
            return formatted_results
            
        except Exception as e:
      
            print(f"Error in MSR_CU_DMM: {str(e)}")
            raise


# def MSR_CU_DMM_user(user_id):
#     """
#     Fetch CU,DMM data in MSR Format including unpaired DMMs, but filtered by current_user_id
#     """

#     with Database.get_session() as db:
#         cu_comp = aliased(EVMComponent, name='cu')
#         dmm_comp = aliased(EVMComponent, name='dmm') 
#         dmm_seal_comp = aliased(EVMComponent, name='dmm_seal')
#         pink_seal_comp = aliased(EVMComponent, name='pink_seal')

#         latest_flc_subquery = db.query(
#             FLCRecord.cu_id,
#             func.max(FLCRecord.flc_date).label('latest_flc_date')
#         ).group_by(FLCRecord.cu_id).subquery()

#         query = db.query(
#             PairingRecord.id.label('pairing_id'),
#             User.username.label('cu_dmm_received'),
#             func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt).label('date_of_receipt'),
#             cu_comp.serial_number.label('control_unit_no'),
#             cu_comp.dom.label('cu_manufacture_date'),
#             cu_comp.box_no.label('cu_box_no'),
#             cu_comp.status.label('present_status_cu'),
#             func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id).label('current_warehouse_id'),
#             func.coalesce(cu_comp.last_received_from_id, dmm_comp.last_received_from_id).label('last_received_from_id'),
#             dmm_comp.serial_number.label('dmm_no'),
#             dmm_comp.dom.label('dmm_manufacture_date'),
#             dmm_comp.status.label('present_status_dmm'),
#             dmm_seal_comp.serial_number.label('dmm_seal_no'),
#             pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'),
#             FLCRecord.flc_date,
#             FLCRecord.passed.label('flc_status'),
#             Warehouse.name.label('cu_warehouse')
#         ).select_from(dmm_comp).filter(
#             dmm_comp.component_type == EVMComponentType.DMM,
#             func.coalesce(cu_comp.current_user_id, dmm_comp.current_user_id) == user_id
#         )

#         query = query.outerjoin(
#             PairingRecord,
#             PairingRecord.id == dmm_comp.pairing_id
#         ).outerjoin(
#             cu_comp,
#             and_(
#                 cu_comp.pairing_id == PairingRecord.id,
#                 cu_comp.component_type == EVMComponentType.CU
#             )
#         ).outerjoin(
#             latest_flc_subquery,
#             latest_flc_subquery.c.cu_id == cu_comp.id
#         ).outerjoin(
#             FLCRecord,
#             and_(
#                 FLCRecord.cu_id == cu_comp.id,
#                 FLCRecord.flc_date == latest_flc_subquery.c.latest_flc_date
#             )
#         ).outerjoin(
#             dmm_seal_comp,
#             and_(
#                 dmm_seal_comp.pairing_id == PairingRecord.id,
#                 dmm_seal_comp.component_type == EVMComponentType.DMM_SEAL
#             )
#         ).outerjoin(
#             pink_seal_comp,
#             and_(
#                 pink_seal_comp.pairing_id == PairingRecord.id,
#                 pink_seal_comp.component_type == EVMComponentType.PINK_PAPER_SEAL
#             )
#         ).outerjoin(
#             Warehouse,
#             Warehouse.id == func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id)
#         ).outerjoin(
#             User,
#             User.id == func.coalesce(cu_comp.last_received_from_id, dmm_comp.last_received_from_id)
#         )

#         results = query.order_by(
#             PairingRecord.id.asc().nulls_last(),
#             dmm_comp.id.asc()
#         ).all()

#         return [
#             {
#                 'sl_no': i,
#                 'cu_dmm_received': row.cu_dmm_received or "",
#                 'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
#                 'control_unit_no': row.control_unit_no or "",
#                 'month_year_manufacture_cu': row.cu_manufacture_date or "",
#                 'dmm_no': row.dmm_no or "",
#                 'month_year_manufacture_dmm': row.dmm_manufacture_date or "",
#                 'dmm_seal_no': row.dmm_seal_no or "",
#                 'cu_pink_paper_seal_no': row.cu_pink_paper_seal_no or "",
#                 'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
#                 'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
#                 'cu_box_no': str(row.cu_box_no) if row.cu_box_no else "",
#                 'cu_warehouse': row.cu_warehouse or "",
#                 'present_status_dmm': row.present_status_dmm or "",
#                 'present_status_cu': row.present_status_cu or ""
#             }
#             for i, row in enumerate(results, 1)
#         ]



def MSR_BU_user(user_id):
    """
    Fetch BU data for components with a user in MSR Format
    """
    
    with Database.get_session() as db:
     
        latest_flc_subquery = db.query(
            FLCBallotUnit.bu_id,
            func.max(FLCBallotUnit.flc_date).label('latest_flc_date')
        ).group_by(FLCBallotUnit.bu_id).subquery()
        
    
        results = db.query(
            EVMComponent.id,
            User.username.label('bu_received_from'),
            EVMComponent.date_of_receipt,
            EVMComponent.serial_number.label('ballot_unit_no'),
            EVMComponent.dom.label('year_of_manufacture'),
            FLCBallotUnit.flc_date,
            FLCBallotUnit.passed.label('flc_status'),
            EVMComponent.box_no.label('bu_box_no'),
            Warehouse.name.label('bu_warehouse')
        ).select_from(EVMComponent)\
        .outerjoin(User, User.id == EVMComponent.last_received_from_id)\
        .outerjoin(
            latest_flc_subquery, 
            latest_flc_subquery.c.bu_id == EVMComponent.id
        )\
        .outerjoin(
            FLCBallotUnit, 
            and_(
                FLCBallotUnit.bu_id == EVMComponent.id,
                FLCBallotUnit.flc_date == latest_flc_subquery.c.latest_flc_date
            )
        )\
        .outerjoin(Warehouse, Warehouse.id == EVMComponent.current_warehouse_id)\
        .filter(
            and_(
                EVMComponent.component_type == EVMComponentType.BU,
                EVMComponent.current_user_id == user_id 
            )
        )\
        .order_by(EVMComponent.id)\
        .all()
        
       
        return [
            {
                'sl_no': i,
                'bu_received_from': row.bu_received_from or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'ballot_unit_no': row.ballot_unit_no or "",
                'year_of_manufacture': row.year_of_manufacture if row.year_of_manufacture else "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                'bu_box_no': str(row.bu_box_no) if row.bu_box_no else "",
                'bu_warehouse': row.bu_warehouse or ""
            }
            for i, row in enumerate(results, 1)
        ]

def MSR_BU():
    """
    Fetch BU data in MSR Format. Used by SEC
    """
    
    with Database.get_session() as db:
     
        latest_flc_subquery = db.query(
            FLCBallotUnit.bu_id,
            func.max(FLCBallotUnit.flc_date).label('latest_flc_date')
        ).group_by(FLCBallotUnit.bu_id).subquery()
        
      
        results = db.query(
            EVMComponent.id,
            User.username.label('bu_received_from'),
            EVMComponent.date_of_receipt,
            EVMComponent.serial_number.label('ballot_unit_no'),
            EVMComponent.dom.label('year_of_manufacture'),
            FLCBallotUnit.flc_date,
            FLCBallotUnit.passed.label('flc_status'),
            EVMComponent.box_no.label('bu_box_no'),
            Warehouse.name.label('bu_warehouse')
        ).select_from(EVMComponent)\
        .outerjoin(User, User.id == EVMComponent.last_received_from_id)\
        .outerjoin(
            latest_flc_subquery, 
            latest_flc_subquery.c.bu_id == EVMComponent.id
        )\
        .outerjoin(
            FLCBallotUnit, 
            and_(
                FLCBallotUnit.bu_id == EVMComponent.id,
                FLCBallotUnit.flc_date == latest_flc_subquery.c.latest_flc_date
            )
        )\
        .outerjoin(Warehouse, Warehouse.id == EVMComponent.current_warehouse_id)\
        .filter(EVMComponent.component_type == EVMComponentType.BU)\
        .order_by(EVMComponent.id)\
        .all()
        
      
        return [
            {
                'sl_no': i,
                'bu_received_from': row.bu_received_from or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'ballot_unit_no': row.ballot_unit_no or "",
                'year_of_manufacture': row.year_of_manufacture if row.year_of_manufacture else "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                'bu_box_no': str(row.bu_box_no) if row.bu_box_no else "",
                'bu_warehouse': row.bu_warehouse or ""
            }
            for i, row in enumerate(results, 1)
        ]
    
def MSR_BU_warehouse(warehouse_id):
    """
    Fetch BU data for components with in a warehouse in MSR Format
    """
    
    with Database.get_session() as db:
     
        latest_flc_subquery = db.query(
            FLCBallotUnit.bu_id,
            func.max(FLCBallotUnit.flc_date).label('latest_flc_date')
        ).group_by(FLCBallotUnit.bu_id).subquery()
        
    
        results = db.query(
            EVMComponent.id,
            User.username.label('bu_received_from'),
            EVMComponent.date_of_receipt,
            EVMComponent.serial_number.label('ballot_unit_no'),
            EVMComponent.dom.label('year_of_manufacture'),
            FLCBallotUnit.flc_date,
            FLCBallotUnit.passed.label('flc_status'),
            EVMComponent.box_no.label('bu_box_no'),
            Warehouse.name.label('bu_warehouse')
        ).select_from(EVMComponent)\
        .outerjoin(User, User.id == EVMComponent.last_received_from_id)\
        .outerjoin(
            latest_flc_subquery, 
            latest_flc_subquery.c.bu_id == EVMComponent.id
        )\
        .outerjoin(
            FLCBallotUnit, 
            and_(
                FLCBallotUnit.bu_id == EVMComponent.id,
                FLCBallotUnit.flc_date == latest_flc_subquery.c.latest_flc_date
            )
        )\
        .outerjoin(Warehouse, Warehouse.id == EVMComponent.current_warehouse_id)\
        .filter(
            and_(
                EVMComponent.component_type == EVMComponentType.BU,
                EVMComponent.current_warehouse_id == warehouse_id 
            )
        )\
        .order_by(EVMComponent.id)\
        .all()
        
       
        return [
            {
                'sl_no': i,
                'bu_received_from': row.bu_received_from or "",
                'date_of_receipt': row.date_of_receipt.strftime("%d/%m/%Y") if row.date_of_receipt else "",
                'ballot_unit_no': row.ballot_unit_no or "",
                'year_of_manufacture': row.year_of_manufacture if row.year_of_manufacture else "",
                'flc_date': row.flc_date.strftime("%d/%m/%Y") if row.flc_date else "",
                'flc_status': "Passed" if row.flc_status else ("Failed" if row.flc_status is not None else ""),
                'bu_box_no': str(row.bu_box_no) if row.bu_box_no else "",
                'bu_warehouse': row.bu_warehouse or ""
            }
            for i, row in enumerate(results, 1)
        ]
    

def MSR_CU_DMM_warehouse(warehouse_id):
    """
    Fetch CU,DMM data in MSR Format for a given warehouse, including unpaired DMMs
    """

    with Database.get_session() as db:
        cu_comp = aliased(EVMComponent, name='cu')
        dmm_comp = aliased(EVMComponent, name='dmm') 
        dmm_seal_comp = aliased(EVMComponent, name='dmm_seal')
        pink_seal_comp = aliased(EVMComponent, name='pink_seal')

        latest_flc_subquery = db.query(
            FLCRecord.cu_id,
            func.max(FLCRecord.flc_date).label('latest_flc_date')
        ).group_by(FLCRecord.cu_id).subquery()

        query = db.query(
            PairingRecord.id.label('pairing_id'),
            User.username.label('cu_dmm_received'),
            func.coalesce(cu_comp.date_of_receipt, dmm_comp.date_of_receipt).label('date_of_receipt'),
            cu_comp.serial_number.label('control_unit_no'),
            cu_comp.dom.label('cu_manufacture_date'),
            cu_comp.box_no.label('cu_box_no'),
            cu_comp.status.label('present_status_cu'),
            func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id).label('current_warehouse_id'),
            func.coalesce(cu_comp.last_received_from_id, dmm_comp.last_received_from_id).label('last_received_from_id'),
            dmm_comp.serial_number.label('dmm_no'),
            dmm_comp.dom.label('dmm_manufacture_date'),
            dmm_comp.status.label('present_status_dmm'),
            dmm_seal_comp.serial_number.label('dmm_seal_no'),
            pink_seal_comp.serial_number.label('cu_pink_paper_seal_no'),
            FLCRecord.flc_date,
            FLCRecord.passed.label('flc_status'),
            Warehouse.name.label('cu_warehouse')
        ).select_from(dmm_comp).filter(
            dmm_comp.component_type == EVMComponentType.DMM,
            func.coalesce(cu_comp.current_warehouse_id, dmm_comp.current_warehouse_id) == warehouse_id
        )

        query = query.outerjoin(
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

        results = query.order_by(
            PairingRecord.id.asc().nulls_last(),
            dmm_comp.id.asc()
        ).all()

        return [
            {
                'sl_no': i,
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
            for i, row in enumerate(results, 1)
        ]

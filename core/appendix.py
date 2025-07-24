from sqlalchemy import func, cast, Integer
from datetime import timedelta, datetime,date
from fastapi.responses import FileResponse
from models.evm import FLCRecord, FLCBallotUnit, EVMComponent
from models.users import User, District  
from annexure.Appendix_1 import appendix_1
from core.db import Database
import os
from sqlalchemy.orm import Session
from typing import Optional
from models.evm import FLCRecord, FLCBallotUnit, EVMComponent
from models.users import District, User
from annexure.Appendix_2 import appendix_2
from annexure.Appendix_3 import appendix_3
from fastapi import BackgroundTasks
from utils.delete_file import remove_file
import tempfile
from typing import List

def generate_daily_flc_report(district_id: int,background_tasks: BackgroundTasks):
   
    with Database.get_session() as db_session:

        district = db_session.query(District).filter(District.id == district_id).first()
        if not district:
            raise ValueError(f"District with ID {district_id} not found")
        
        district_name = district.name
        daily_data = []
        current_date = datetime.now()
        
    
        cu_dates = db_session.query(func.date(FLCRecord.flc_date)).join(
            User, FLCRecord.flc_by_id == User.id
        ).filter(
            FLCRecord.passed == True,
            User.district_id == district_id
        ).distinct().all()
        
  
        bu_dates = db_session.query(func.date(FLCBallotUnit.flc_date)).join(
            User, FLCBallotUnit.flc_by_id == User.id
        ).filter(
            FLCBallotUnit.passed == True,
            User.district_id == district_id
        ).distinct().all()
        

        all_dates = set()
        for date_tuple in cu_dates:
            all_dates.add(date_tuple[0])
        for date_tuple in bu_dates:
            all_dates.add(date_tuple[0])
        
        sorted_dates = sorted(all_dates)
        
        for date in sorted_dates:
       
            cu_till_date = db_session.query(FLCRecord).join(
                User, FLCRecord.flc_by_id == User.id
            ).filter(
                func.date(FLCRecord.flc_date) <= date,
                FLCRecord.passed == True,
                User.district_id == district_id
            ).count()
            
          
            bu_till_date = db_session.query(FLCBallotUnit).join(
                User, FLCBallotUnit.flc_by_id == User.id
            ).filter(
                func.date(FLCBallotUnit.flc_date) <= date,
                FLCBallotUnit.passed == True,
                User.district_id == district_id
            ).count()
            
     
            cu_on_date = db_session.query(FLCRecord).join(
                User, FLCRecord.flc_by_id == User.id
            ).filter(
                func.date(FLCRecord.flc_date) == date,
                FLCRecord.passed == True,
                User.district_id == district_id
            ).count()
            
      
            bu_on_date = db_session.query(FLCBallotUnit).join(
                User, FLCBallotUnit.flc_by_id == User.id
            ).filter(
                func.date(FLCBallotUnit.flc_date) == date,
                FLCBallotUnit.passed == True,
                User.district_id == district_id
            ).count()
            
            daily_data.append({
                'date': date.strftime("%d-%m-%Y"),
                'cu_till_date': cu_till_date,
                'bu_till_date': bu_till_date,
                'cu_on_date': cu_on_date,
                'bu_on_date': bu_on_date,
                'remarks': ""
            })
 
        pdf_path = appendix_1(daily_data, district_name)
        filename = os.path.basename(pdf_path) 

        if os.path.exists(pdf_path):
            background_tasks.add_task(remove_file, filename)
            return FileResponse(
                path=pdf_path,
                filename=filename,
                media_type='application/pdf',
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            raise FileNotFoundError(f"Generated PDF file not found at {pdf_path}")




completion_date = datetime.now().strftime('%Y-%m-%d')

def generate_flc_appendix2(district_id: int,background_tasks: BackgroundTasks):
 
    
    # Set completion_date and end_date to current date (outside session)
    
    end_date = date.today()
    
    with Database.get_session() as db:
        district = db.query(District.name).filter(District.id == district_id).scalar()
        if not district:
            raise ValueError(f"District {district_id} not found")
        
        user_ids = [u[0] for u in db.query(User.id).filter(User.district_id == district_id).all()]
        
        # Find the oldest date in the database from both tables
        oldest_cu_date = db.query(func.min(func.date(FLCRecord.flc_date))).filter(
            FLCRecord.flc_by_id.in_(user_ids) if user_ids else False
        ).scalar()
        
        oldest_bu_date = db.query(func.min(func.date(FLCBallotUnit.flc_date))).filter(
            FLCBallotUnit.flc_by_id.in_(user_ids) if user_ids else False
        ).scalar()
        
        # Determine the overall oldest date
        start_date = None
        if oldest_cu_date and oldest_bu_date:
            start_date = min(oldest_cu_date, oldest_bu_date)
        elif oldest_cu_date:
            start_date = oldest_cu_date
        elif oldest_bu_date:
            start_date = oldest_bu_date
        
        if not user_ids:
            flc_data = [{
                'cu_total': 0, 'bu_total': 0, 'cu_passed': 0, 'bu_passed': 0,
                'cu_failed': 0, 'bu_failed': 0, 'remarks': 'No users found'
            }]
        else:
            cu_query = db.query(
                func.count(FLCRecord.id).label('total'),
                func.coalesce(func.sum(cast(FLCRecord.passed, Integer)), 0).label('passed')
            ).filter(FLCRecord.flc_by_id.in_(user_ids))
            
            if start_date:
                cu_query = cu_query.filter(func.date(FLCRecord.flc_date) >= start_date)
            cu_query = cu_query.filter(func.date(FLCRecord.flc_date) <= end_date)
            
            cu_stats = cu_query.first()
            cu_total = cu_stats.total if cu_stats.total else 0
            cu_passed = cu_stats.passed if cu_stats.passed else 0
            cu_failed = cu_total - cu_passed
            
            bu_query = db.query(
                func.count(FLCBallotUnit.id).label('total'),
                func.coalesce(func.sum(cast(FLCBallotUnit.passed, Integer)), 0).label('passed')
            ).filter(FLCBallotUnit.flc_by_id.in_(user_ids))
            
            if start_date:
                bu_query = bu_query.filter(func.date(FLCBallotUnit.flc_date) >= start_date)
            bu_query = bu_query.filter(func.date(FLCBallotUnit.flc_date) <= end_date)
            
            bu_stats = bu_query.first()
            bu_total = bu_stats.total if bu_stats.total else 0
            bu_passed = bu_stats.passed if bu_stats.passed else 0
            bu_failed = bu_total - bu_passed
            
            remarks = "FLC completed"
            if cu_total > 0 and (cu_passed / cu_total) < 0.9:
                remarks = f"CU pass rate: {(cu_passed/cu_total*100):.1f}%"
            if bu_total > 0 and (bu_passed / bu_total) < 0.9:
                if "CU pass rate" in remarks:
                    remarks += f", BU pass rate: {(bu_passed/bu_total*100):.1f}%"
                else:
                    remarks = f"BU pass rate: {(bu_passed/bu_total*100):.1f}%"
            
            flc_data = [{
                'cu_total': cu_total,
                'bu_total': bu_total,
                'cu_passed': cu_passed,
                'bu_passed': bu_passed,
                'cu_failed': cu_failed,
                'bu_failed': bu_failed,
                'remarks': remarks
            }]
        
        pdf_path = appendix_2(flc_data, district)  # Now returns full path
        filename = os.path.basename(pdf_path)      # Extract filename for response

        background_tasks.add_task(remove_file, pdf_path)

        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=filename
        )


def generate_appendix3_for_district(
    district_id: int,
    joining_date: str, 
    members: List[str], 
    free_accommodation: bool, 
    local_conveyance: bool, 
    relieving_date: str, 
    background_tasks: BackgroundTasks
):
    with Database.get_session() as db:
        cast_type = Integer  # Use SQLAlchemy Integer type
        
        cu_stats = db.query(
            func.count(FLCRecord.id).label('total'),
            func.sum(func.cast(FLCRecord.passed, cast_type)).label('passed')
        ).join(User, FLCRecord.flc_by_id == User.id).filter(
            User.district_id == district_id
        ).first()

        bu_stats = db.query(
            func.count(FLCBallotUnit.id).label('total'),
            func.sum(func.cast(FLCBallotUnit.passed, cast_type)).label('passed')
        ).join(User, FLCBallotUnit.flc_by_id == User.id).filter(
            User.district_id == district_id
        ).first()

        
        cu_tested = cu_stats.total if cu_stats.total else 0
        cu_passed = cu_stats.passed if cu_stats.passed else 0
        cu_rejected = cu_tested - cu_passed
        
        
        
        bu_tested = bu_stats.total if bu_stats.total else 0
        bu_passed = bu_stats.passed if bu_stats.passed else 0
        bu_rejected = bu_tested - bu_passed
        
        evm_data = {
            'cu_tested': cu_tested,
            'cu_passed': cu_passed,
            'cu_rejected': cu_rejected,
            'bu_tested': bu_tested,
            'bu_passed': bu_passed,
            'bu_rejected': bu_rejected
        }
        
        pdf_path = appendix_3(
            joining_date=joining_date,
            members=members,
            evm_data=evm_data,
            free_accommodation=free_accommodation,
            local_conveyance=local_conveyance,
            relieving_date=relieving_date,
  
        )

        filename = os.path.basename(pdf_path)

        background_tasks.add_task(remove_file, filename)

        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
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

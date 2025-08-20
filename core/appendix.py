from sqlalchemy import func, cast, Integer,distinct, or_
from datetime import timedelta, datetime,date
from fastapi.responses import FileResponse
from models.evm import FLCRecord, FLCBallotUnit, EVMComponent
from models.users import User, District  
from annexure.Appendix_1 import appendix_1
from core.db import Database
import os
from models.evm import FLCRecord, FLCBallotUnit, EVMComponent,EVMComponentType
from models.users import District, User
from annexure.Appendix_2 import appendix_2
from annexure.Appendix_3 import appendix_3
from fastapi import BackgroundTasks
from utils.delete_file import remove_file
from annexure.daily_report import daily_report
from typing import List
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from typing import List, Dict, Tuple
import logging

def generate_daily_flc_report(district_id: int, background_tasks: BackgroundTasks):
    with Database.get_session() as db_session:
        # Validate district exists
        district = db_session.query(District).filter(District.id == district_id).first()
        if not district:
            raise ValueError(f"District with ID {district_id} not found")
        
        district_name = district.name
        
        # Get user IDs as a subquery for better performance
        user_subquery = db_session.query(User.id).filter(User.district_id == district_id).subquery()
        
        # CU data with INNER JOIN to ensure component validity
        cu_data = db_session.query(
            func.date(FLCRecord.flc_date).label('date'),
            func.count(distinct(FLCRecord.id)).label('count')
        ).join(
            # Join with any valid component
            EVMComponent,
            or_(
                FLCRecord.cu_id == EVMComponent.id,
                FLCRecord.dmm_id == EVMComponent.id,
                FLCRecord.dmm_seal_id == EVMComponent.id,
                FLCRecord.pink_paper_seal_id == EVMComponent.id
            )
        ).join(
            user_subquery,
            FLCRecord.flc_by_id == user_subquery.c.id
        ).filter(
            FLCRecord.passed == True
        ).group_by(
            func.date(FLCRecord.flc_date)
        ).order_by(
            func.date(FLCRecord.flc_date)
        ).all()
        
        # BU data with INNER JOIN to ensure component validity
        bu_data = db_session.query(
            func.date(FLCBallotUnit.flc_date).label('date'),
            func.count(FLCBallotUnit.id).label('count')
        ).join(
            EVMComponent,
            FLCBallotUnit.bu_id == EVMComponent.id
        ).join(
            user_subquery,
            FLCBallotUnit.flc_by_id == user_subquery.c.id
        ).filter(
            FLCBallotUnit.passed == True
        ).group_by(
            func.date(FLCBallotUnit.flc_date)
        ).order_by(
            func.date(FLCBallotUnit.flc_date)
        ).all()
        
        # Process data same as main function
        cu_dict = {row.date: row.count for row in cu_data}
        bu_dict = {row.date: row.count for row in bu_data}
        all_dates = sorted(set(cu_dict.keys()) | set(bu_dict.keys()))
        
        if not all_dates:
            daily_data = []
        else:
            daily_data = []
            cu_running_total = 0
            bu_running_total = 0
            
            for i, current_date in enumerate(all_dates):
                cu_on_date = cu_dict.get(current_date, 0)
                bu_on_date = bu_dict.get(current_date, 0)
                
                if i == 0:  # Oldest date
                    cu_till_date = 0
                    bu_till_date = 0
                else:
                    cu_till_date = cu_running_total
                    bu_till_date = bu_running_total
                
                daily_data.append({
                    'date': current_date.strftime("%d-%m-%Y"),
                    'cu_till_date': cu_till_date,
                    'bu_till_date': bu_till_date,
                    'cu_on_date': cu_on_date,
                    'bu_on_date': bu_on_date,
                    'remarks': " "
                })
                
                cu_running_total += cu_on_date
                bu_running_total += bu_on_date
        
        # Generate PDF report
        try:
            pdf_path = appendix_1(daily_data, district_name)
            filename = os.path.basename(pdf_path)

            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"Generated PDF file not found at {pdf_path}")
                
            background_tasks.add_task(remove_file, filename)
            return FileResponse(
                path=pdf_path,
                filename=filename,
                media_type='application/pdf',
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate FLC report for district {district_id}: {str(e)}")
        
def generate_flc_appendix2(district_id: int, background_tasks: BackgroundTasks):
    end_date = date.today()
    
    with Database.get_session() as db:
        district_name = db.query(District.name).filter(District.id == district_id).scalar()
        if not district_name:
            raise ValueError(f"District {district_id} not found")
        
        user_ids = [u[0] for u in db.query(User.id).filter(User.district_id == district_id).all()]
        
        if not user_ids:
            flc_data = [{
                'cu_total': 0, 'bu_total': 0, 'cu_passed': 0, 'bu_passed': 0,
                'cu_failed': 0, 'bu_failed': 0, 'remarks': '  '
            }]
        else:
            oldest_cu_date = db.query(func.min(func.date(FLCRecord.flc_date))).filter(
                FLCRecord.flc_by_id.in_(user_ids)
            ).scalar()
            
            oldest_bu_date = db.query(func.min(func.date(FLCBallotUnit.flc_date))).filter(
                FLCBallotUnit.flc_by_id.in_(user_ids)
            ).scalar()
            
            start_date = None
            if oldest_cu_date and oldest_bu_date:
                start_date = min(oldest_cu_date, oldest_bu_date)
            elif oldest_cu_date:
                start_date = oldest_cu_date
            elif oldest_bu_date:
                start_date = oldest_bu_date
            
            if start_date == end_date:
                flc_data = [{
                    'cu_total': 0, 'bu_total': 0, 'cu_passed': 0, 'bu_passed': 0,
                    'cu_failed': 0, 'bu_failed': 0, 'remarks': ' '
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
                
                remarks = " "
                
                flc_data = [{
                    'cu_total': cu_total,
                    'bu_total': bu_total,
                    'cu_passed': cu_passed,
                    'bu_passed': bu_passed,
                    'cu_failed': cu_failed,
                    'bu_failed': bu_failed,
                    'remarks': remarks
                }]
        
        pdf_path = appendix_2(flc_data, district_name)
        filename = os.path.basename(pdf_path)

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


def get_flc_report_data(report_date: str) -> Tuple[List[Dict], str, Dict]:
    try:
        try:
            target_date = datetime.strptime(report_date, "%d-%m-%Y").date()
        except ValueError:
            raise ValueError(f"Invalid date format. Expected DD-MM-YYYY, got: {report_date}")
        
        previous_date = target_date - timedelta(days=1)
        
        with Database.get_session() as db:
            kerala_districts = [
                "Thiruvananthapuram", "Kollam", "Pathanamthitta", "Alappuzha",
                "Kottayam", "Idukki", "Ernakulam", "Thrissur", "Palakkad",
                "Malappuram", "Kozhikode", "Wayanad", "Kannur", "Kasaragod"
            ]
            
            results = db.query(
                District.name.label('district_name'),
                EVMComponent.component_type,
                EVMComponent.status,
                EVMComponent.date_of_receipt,
                func.count(EVMComponent.id).label('count')
            ).join(
                User, EVMComponent.current_user_id == User.id
            ).join(
                District, User.district_id == District.id
            ).filter(
                District.name.in_(kerala_districts),
                EVMComponent.component_type.in_([EVMComponentType.CU, EVMComponentType.BU]),
                EVMComponent.date_of_receipt.isnot(None),
                EVMComponent.status.in_(["FLC_Passed", "FLC_Failed"]),
                EVMComponent.date_of_receipt <= target_date
            ).group_by(
                District.name,
                EVMComponent.component_type,
                EVMComponent.status,
                EVMComponent.date_of_receipt
            ).all()
            
            district_stats = {name: {
                'cu_till_pass': 0, 'cu_till_fail': 0,
                'bu_till_pass': 0, 'bu_till_fail': 0,
                'cu_on_pass': 0, 'cu_on_fail': 0,
                'bu_on_pass': 0, 'bu_on_fail': 0
            } for name in kerala_districts}
            
            totals = {
                'cu_till_pass': 0, 'cu_till_fail': 0,
                'bu_till_pass': 0, 'bu_till_fail': 0,
                'cu_on_pass': 0, 'cu_on_fail': 0,
                'bu_on_pass': 0, 'bu_on_fail': 0
            }
            
            for district_name, component_type, status, date_of_receipt, count in results:
                comp_key = 'cu' if component_type == EVMComponentType.CU else 'bu'
                status_key = 'pass' if status == "FLC_Passed" else 'fail'
                
                if date_of_receipt == target_date:
                    key = f"{comp_key}_on_{status_key}"
                elif date_of_receipt <= previous_date:
                    key = f"{comp_key}_till_{status_key}"
                else:
                    continue
                
                district_stats[district_name][key] += count
                totals[key] += count
            
            district_data = []
            for district_name in kerala_districts:
                stats = district_stats[district_name]
                district_row = {'district': district_name, **stats}
                district_data.append(district_row)
            
            formatted_date = target_date.strftime("%d/%m/%Y")
            
            logging.info(f"Successfully fetched FLC data for {len(district_data)} districts on {formatted_date}")
            return district_data, formatted_date, totals
            
    except ValueError as ve:
        logging.error(f"Date parsing error: {str(ve)}")
        raise ve
    except Exception as e:
        logging.error(f"Error fetching FLC report data: {str(e)}")
        raise Exception(f"Failed to fetch FLC report data: {str(e)}")
    
def generate_flc_report_sec(background_tasks: BackgroundTasks,report_date: str) -> str:
    try:
        
        district_data, formatted_date, totals = get_flc_report_data(report_date)
        
        pdf_path = daily_report(district_data, formatted_date, totals)
        background_tasks.add_task(remove_file, pdf_path)
        logging.info(f"Successfully generated FLC daily report: {pdf_path}")
        return FileResponse(
                path=pdf_path,
                media_type='application/pdf',
                headers={"Content-Disposition": f"attachment; filename={pdf_path}"}
            )
        
    except Exception as e:
        logging.error(f"Error generating FLC daily report: {str(e)}")
        raise Exception(f"Failed to generate FLC daily report: {str(e)}")
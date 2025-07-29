from fastapi import APIRouter, Depends, BackgroundTasks, Request
from annexure.N_35 import Form_N35, EVMPair
from annexure.N_36 import Form_N36
from annexure.pairing_sticker import pairing_sticker, EVMData
from utils.authtoken import get_current_user
from fastapi.responses import FileResponse
from core.appendix import generate_daily_flc_report, generate_flc_appendix2, generate_appendix3_for_district,generate_flc_report_sec
from pydantic import BaseModel
from typing import List
import uuid
from utils.rate_limiter import limiter
from core.flc import generate_dmm_flc_pdf,generate_bu_flc_pdf,generate_cu_flc_pdf
from annexure.box_wise_sticker import Box_wise_sticker
from utils.delete_file import remove_file

router = APIRouter()


class Component(BaseModel):
    serial_no: str
    status: str
    flc_date: str

class Box(BaseModel):
    box_no: str
    components: List[Component]

class BoxStickerRequest(BaseModel):
    boxes_data: List[Box]
    
class Appendix3(BaseModel):
    districtid: int
    joining_date: str
    members: List[str]
    free_accommodation: bool
    local_conveyance: bool 
    relieving_date: str

@router.post("/N35")
@limiter.limit("5/minute")
async def get_N35(request: Request, data: EVMPair, allotment_order_no: str, current_user: dict = Depends(get_current_user)):
    try:
        filename = f"Form_N35_{allotment_order_no}_{uuid.uuid4().hex}.pdf"
        return Form_N35(data, allotment_order_no, filename)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Form N-35"}
    
@router.post("/N36")
@limiter.limit("5/minute")
async def get_N36(request: Request, data: EVMPair, allotment_order_no: str, current_user: dict = Depends(get_current_user)):
    try:
        filename = f"Form_N36_{allotment_order_no}_{uuid.uuid4().hex}.pdf"
        return Form_N36(data, allotment_order_no, filename)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Form N-36"}
    
@router.post("/pairing_sticker")
@limiter.limit("5/minute")
async def get_pairing_sticker(request: Request, data_list: list[EVMData], current_user: dict = Depends(get_current_user)):
    try:
        return pairing_sticker(data_list, filename=f"pairing_sticker_{uuid.uuid4().hex}.pdf")
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate pairing sticker"}

@router.post("/box-sticker")
@limiter.limit("5/minute")
async def get_box_sticker(request: Request, data: BoxStickerRequest, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    filename = f"box_wise_sticker_{uuid.uuid4().hex}.pdf"   
    pdf = Box_wise_sticker(data.boxes_data, filename)
    background_tasks.add_task(remove_file, filename)
    return FileResponse(pdf, media_type='application/pdf', filename=filename)
        
@router.get("/templates/add/{component_type}")
@limiter.limit("5/minute")
async def get_add_template(request: Request, component_type: str, current_user: dict = Depends(get_current_user)):
    return FileResponse(path=f"templates/Add_{component_type}.xlsx", media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"Add_{component_type}")

@router.get("/templates/flc/{component_type}")
@limiter.limit("5/minute")
async def get_flc_template(request: Request, component_type: str, current_user: dict = Depends(get_current_user)):
    return FileResponse(path=f"templates/FLC_{component_type}.xlsx", media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"FLC_{component_type}")

@router.get("/annexure-2")
@limiter.limit("5/minute")
async def get_attendance_reg(request: Request, current_user: dict = Depends(get_current_user)):
    return FileResponse(path="templates/Attendance.pdf", media_type="application/pdf", filename="Annexure-II")

@router.get("/annexure-4")
@limiter.limit("5/minute")
async def get_attendance_reg(request: Request, current_user: dict = Depends(get_current_user)):
    return FileResponse(path="templates/Physical_Verification.pdf", media_type="application/pdf", filename="Annexure-IV")

@router.get("/appendix-1/{districtid}")
@limiter.limit("5/minute")
async def get_appendix_1(request: Request, districtid: int, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    try:
        return generate_daily_flc_report(districtid, background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Appendix 1"}
    
@router.get("/appendix-2/{districtid}")
@limiter.limit("5/minute")
async def get_appendix_2(request: Request, districtid: int, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    try:
        return generate_flc_appendix2(districtid, background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Appendix 2"}

@router.post("/appendix-3")
@limiter.limit("5/minute")
async def get_appendix_3(request: Request, data: Appendix3, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    try:
        return generate_appendix3_for_district(
            district_id=data.districtid,
            joining_date=data.joining_date,
            members=data.members,
            free_accommodation=data.free_accommodation,
            local_conveyance=data.local_conveyance,
            relieving_date=data.relieving_date,
            background_tasks=background_tasks
        )
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Appendix 3"}
    
@router.get("/annexure-3/DMM/{district_id}")
async def get_dmm_flc_pdf(request: Request, district_id: str, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    try:
        return generate_dmm_flc_pdf(district_id, background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate DMM FLC PDF"}
    
@router.get("/annexure-3/CU/{district_id}")
async def get_cu_flc_pdf(request: Request, district_id: str, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    try:
        return generate_cu_flc_pdf(district_id, background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate CU FLC PDF"}
    
@router.get("/annexure-3/BU/{district_id}")
async def get_bu_flc_pdf(request: Request, district_id: str, background_tasks: BackgroundTasks,current_user: dict = Depends(get_current_user)):
    try:
        return generate_bu_flc_pdf(district_id, background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate BU FLC PDF"}

@router.get("/flc/daily-report")
async def get_daily_report(request: Request, background_tasks: BackgroundTasks):
    return generate_flc_report_sec(background_tasks)
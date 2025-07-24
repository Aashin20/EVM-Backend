from fastapi import APIRouter,Depends,BackgroundTasks
from annexure.N_35 import Form_N35,EVMPair
from annexure.N_36 import Form_N36
from annexure.pairing_sticker import pairing_sticker,EVMData
from utils.authtoken import get_current_user
from core.flc import generate_box_wise_sticker
from fastapi.responses import FileResponse
from core.appendix import generate_daily_flc_report,generate_flc_appendix2, generate_appendix3_for_district
from pydantic import BaseModel
from typing import List
import uuid

router = APIRouter()

class Appendix3(BaseModel):
    districtid: int
    joining_date: str
    members: List[str]
    free_accommodation: bool
    local_conveyance: bool 
    relieving_date: str

@router.post("/N35")
async def get_N35(data: EVMPair,allotment_order_no: str,current_user: dict=Depends(get_current_user)):
    try:
        filename = f"Form_N35_{allotment_order_no}_{uuid.uuid4().hex}.pdf"
        return Form_N35(data, allotment_order_no, filename)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Form N-35"}
    
@router.post("/N36")
async def get_N36(data: EVMPair,allotment_order_no: str,current_user: dict=Depends(get_current_user)):
    try:
        filename = f"Form_N36_{allotment_order_no}_{uuid.uuid4().hex}.pdf"
        return Form_N36(data, allotment_order_no, filename)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Form N-36"}
    
@router.post("/pairing_sticker")
async def get_pairing_sticker(data_list: list[EVMData], current_user: dict = Depends(get_current_user)):
    try:
        return pairing_sticker(data_list, filename=f"pairing_sticker_{uuid.uuid4().hex}.pdf")
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate pairing sticker"}
    
@router.get("/box-sticker/{district_id}")
async def get_box_sticker(district_id:str,current_user: dict = Depends(get_current_user)):
    return generate_box_wise_sticker(district_id)

@router.get("/templates/add/{component_type}")
async def get_add_template(component_type:str,current_user: dict=Depends(get_current_user)):
    return FileResponse(path=f"templates/Add_{component_type}.xlsx",media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=f"Add_{component_type}")

@router.get("/templates/flc/{component_type}")
async def get_flc_template(component_type:str,current_user: dict=Depends(get_current_user)):
    return FileResponse(path=f"templates/FLC_{component_type}.xlsx",media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename=f"FLC_{component_type}")

@router.get("/annexure-2")
async def get_attendance_reg(current_user: dict=Depends(get_current_user)):
    return FileResponse(path="templates/Attendance.pdf",media_type="application/pdf",filename="Annexure-II")

@router.get("/annexure-4")
async def get_attendance_reg(current_user: dict=Depends(get_current_user)):
    return FileResponse(path="templates/Physical_Verification.pdf",media_type="application/pdf",filename="Annexure-IV")

@router.get("/appendix-1/{districtid}")
async def get_appendix_1(districtid: int,background_tasks: BackgroundTasks):
    try:
        return generate_daily_flc_report(districtid,background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Appendix 1"}
    
@router.get("/appendix-2/{districtid}")
async def get_appendix_2(districtid: int,background_tasks: BackgroundTasks):
    try:
        return generate_flc_appendix2(districtid,background_tasks)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Appendix 2"}


@router.post("/appendix-3")
async def get_appendix_3(data: Appendix3,background_tasks: BackgroundTasks):
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
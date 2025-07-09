from fastapi import APIRouter,Depends
from annexure.N_35 import Form_N35,EVMPair
from annexure.N_36 import Form_N36
from annexure.pairing_sticker import pairing_sticker,EVMData
from utils.authtoken import get_current_user
from core.flc import generate_box_wise_sticker
from fastapi.responses import FileResponse

router = APIRouter()

@router.post("/N35")
async def get_N35(data: EVMPair,allotment_order_no: str,current_user: dict=Depends(get_current_user)):
    try:
        filename = f"Form_N35_{allotment_order_no}.pdf"
        return Form_N35(data, allotment_order_no, filename)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Form N-35"}
    
@router.post("/N36")
async def get_N36(data: EVMPair,allotment_order_no: str,current_user: dict=Depends(get_current_user)):
    try:
        filename = f"Form_N36_{allotment_order_no}.pdf"
        return Form_N36(data, allotment_order_no, filename)
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate Form N-36"}
    
@router.post("/pairing_sticker")
async def get_pairing_sticker(data_list: list[EVMData], current_user: dict = Depends(get_current_user)):
    try:
        return pairing_sticker(data_list, filename="pairing_sticker.pdf")
    except Exception as e:
        return {"error": str(e), "message": "Failed to generate pairing sticker"}
    
@router.get("/box-sticker/{district_id}")
async def get_box_sticker(district_id:str,current_user: dict = Depends(get_current_user)):
    return generate_box_wise_sticker(district_id)
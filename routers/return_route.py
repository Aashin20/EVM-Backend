from core.return_ import status_change
from fastapi import APIRouter

router = APIRouter()


@router.get('/{local_body_id}/{status}')
async def to_polling(local_body_id:str,status:str):
    return status_change(local_body_id,status)
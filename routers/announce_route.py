from core.announcements import create_announcement,view_announcements
from fastapi import APIRouter,Depends
from utils.authtoken import get_current_user

router = APIRouter()

@router.post("/create")
async def create_announce(content: str,to_user: str,from_user_id: dict = Depends(get_current_user)):
    return create_announcement(content,from_user_id['user_id'],to_user)

@router.get("/view")
async def get_announce(current_user: dict = Depends(get_current_user)):
    return view_announcements(current_user['user_id'],current_user['role'])
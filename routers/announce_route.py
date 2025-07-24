from fastapi import APIRouter, Depends, Request
from utils.authtoken import get_current_user
from utils.rate_limiter import limiter
from core.announcements import create_announcement, view_announcements

router = APIRouter()

@router.post("/create")
@limiter.limit("30/minute")
async def create_announce(
    request: Request,  
    title: str,
    content: str,
    to_user: str,
    tag: str,
    from_user_id: dict = Depends(get_current_user)
):
    return create_announcement(title, content, tag, from_user_id['user_id'], to_user)

@router.get("/view")
@limiter.limit("30/minute")
async def get_announce(
    request: Request,  
    current_user: dict = Depends(get_current_user)
):
    return view_announcements(current_user['user_id'], current_user['role'])

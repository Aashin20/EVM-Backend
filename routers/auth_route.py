from fastapi import APIRouter
from core.user import register, login
from core.user import RegisterModel

router = APIRouter()

@router.post("/login")
async def login_user(username: str, password: str):
    return login(username, password)
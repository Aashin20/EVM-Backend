from fastapi import APIRouter
from core.user import register, login
from core.user import LoginModel

router = APIRouter()

@router.post("/login")
async def login_user(data: LoginModel):
    return login(data)
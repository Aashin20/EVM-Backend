from fastapi import APIRouter
from core.auth import register, login
from core.auth import RegisterModel

router = APIRouter()

@router.post("/register")
async def register_user(details: RegisterModel):
    return register(details)


@router.post("/login")
async def login_user(username: str, password: str):
    return login(username, password)
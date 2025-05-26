from fastapi import APIRouter
from core.auth import register, login

router = APIRouter()

@router.post("/register")
async def register_user(username: str, password: str, role: str):
    return register(username, password, role)


@router.post("/login")
async def login_user(username: str, password: str):
    return login(username, password)
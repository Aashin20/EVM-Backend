from utils.authtoken import create_token, verify_token
from .db import Database
from models.users import User
import bcrypt
from pydantic import BaseModel, constr
from typing import Optional
from sqlalchemy.orm import joinedload

class RegisterModel(BaseModel):
    username: constr(strip_whitespace=True, min_length=3)
    password: constr(min_length=6)
    role_id: int
    level_id: int
    district_id: int
    local_body_id: Optional[int] = None
    warehouse_id: Optional[int] = None


def login(username, password):

    with Database.get_session() as session:
        current = session.query(User).options(
            joinedload(User.role),
            joinedload(User.level)
        ).filter(User.username == username).first()
        if not current:
            return {"error": "User not found"}
        if current.is_active is False:
            return {"error": "Account has been deactivated, Please contact support"}

    password_hash = current.password_hash
    verification = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    if not verification:
        return {"error": "Invalid password"}

    token = create_token({"username": current.username, "role": current.role.name,"level": current.level.name, "user_id": current.id})

    return {"token": token, "role": current.role, "username": current.username}




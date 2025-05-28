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



def register(details: RegisterModel):
    with Database.get_session() as session:
        existing_user = session.query(User).filter(User.username == details.username).first()
        if existing_user:
            return {"error": "Username already exists"}
        
        hashed_password = bcrypt.hashpw(details.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        local_body_id = details.local_body_id if details.local_body_id not in [0, "0"] else None
        warehouse_id = details.warehouse_id if details.warehouse_id not in [0, "0"] else None
        new_user = User(
            username=details.username,
            password_hash=hashed_password,
            role_id=details.role_id,
            level_id=details.level_id,
            district_id=details.district_id,
            local_body_id=local_body_id,
            warehouse_id=warehouse_id
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        role_name = new_user.role.name
        level_name = new_user.level.name
        user_id = new_user.id
        username = new_user.username

    token = create_token({
        "username": username,
        "role": role_name,
        "level": level_name,
        "user_id": user_id
    })

    return {
        "token": token,
        "role": role_name,
        "level": level_name,
        "user_id": user_id
    }


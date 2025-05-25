from utils.authtoken import create_token, verify_token
from .db import Database
from models.users import User
import bcrypt



def login(username, password):

    with Database.get_session() as session:
        current = session.query(User).filter(User.username == username).first()
        if not current:
            return {"error": "User not found"}

    password_hash = current.password_hash
    verification = bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    if not verification:
        return {"error": "Invalid password"}

    token = create_token({"username": current.username, "role": current.role})

    return {"token": token, "role": current.role, "username": current.username}



def register(username, password, role):
    with Database.get_session() as session:
        existing_user = session.query(User).filter(User.username == username).first()
        if existing_user:
            return {"error": "Username already exists"}

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(username=username, password_hash=hashed_password, role=role)
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

    token = create_token({"username": new_user.username, "role": new_user.role})
    return {"token": token, "role": new_user.role, "username": new_user.username}
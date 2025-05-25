from jose import jwt, ExpiredSignatureError, JWTError
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from fastapi import HTTPException

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def create_token(details: dict, expiry: int = 30):
    to_encode = details.copy()
    expire = datetime.now() + timedelta(minutes=expiry)
    to_encode.update({"exp": expire})
    jwt_token = jwt.encode(to_encode, SECRET_KEY, ALGORITHM)
    return jwt_token


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        return {"error": str(e)}
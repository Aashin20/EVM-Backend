from jose import jwt, ExpiredSignatureError, JWTError
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
import uuid
from fastapi import Depends, HTTPException, status, Request, Response
import logging
from typing import Dict, Tuple
from slowapi import Limiter

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", SECRET_KEY + "_refresh")
ALGORITHM = "HS256"
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"

ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
REFRESH_TOKEN_EXPIRE_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

active_refresh_tokens = set()

def create_tokens(user_data: dict) -> Tuple[str, str]:
    now = datetime.now(timezone.utc)
    access_payload = user_data.copy()
    access_payload.update({
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access"
    })
    access_token = jwt.encode(access_payload, SECRET_KEY, ALGORITHM)
    refresh_jti = str(uuid.uuid4())
    refresh_payload = {
        "sub": user_data.get("sub"),
        "user_id": user_data.get("user_id"),
        "jti": refresh_jti,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh"
    }
    refresh_token = jwt.encode(refresh_payload, REFRESH_SECRET_KEY, ALGORITHM)
    active_refresh_tokens.add(refresh_jti)
    return access_token, refresh_token

def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, [ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid access token")

def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, [ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        jti = payload.get("jti")
        if jti not in active_refresh_tokens:
            raise HTTPException(status_code=401, detail="Refresh token revoked")
        return payload
    except ExpiredSignatureError:
        try:
            jti = jwt.decode(token, REFRESH_SECRET_KEY, [ALGORITHM], options={"verify_exp": False}).get("jti")
            active_refresh_tokens.discard(jti)
        except:
            pass
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

def revoke_refresh_token(jti: str):
    active_refresh_tokens.discard(jti)

def get_current_user(request: Request):
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    user = verify_access_token(access_token)
    request.state.user_id = user["user_id"]
    return user

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    cookie_settings = {
        "httponly": True,
        "path": "/",
        "samesite": "none",
        "secure": True
    }
    if IS_PRODUCTION:
        cookie_settings["secure"] = True
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_settings
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **cookie_settings
    )

def clear_auth_cookies(response: Response):
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")

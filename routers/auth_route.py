from fastapi import APIRouter, Response, Request, Depends
# from core.user import register, login
from core.user import LoginModel
from utils.authtoken import (create_tokens,set_auth_cookies,active_refresh_tokens,verify_access_token, verify_refresh_token, 
                             revoke_refresh_token, get_current_user, clear_auth_cookies,REFRESH_COOKIE_NAME, 
                             ACCESS_COOKIE_NAME,REFRESH_SECRET_KEY,ALGORITHM)
from fastapi import HTTPException, status
from fastapi.logger import logger
from sqlalchemy.orm import joinedload
from core.db import Database
from models.users import User
from pydantic import BaseModel, constr
import bcrypt
from jose import jwt

router = APIRouter()

class LoginModel(BaseModel):
    username: constr(strip_whitespace=True, min_length=3)
    password: constr(min_length=6)

@router.post('/login')
async def login(response: Response, data: LoginModel):
    try:
        with Database.get_session() as session:
            current = session.query(User).options(
                joinedload(User.role),
                joinedload(User.level)
            ).filter(User.username == data.username).first()
            
            if not current:
                raise HTTPException(status_code=401, detail="Invalid credentials")  
            
            if current.is_active is False:
                raise HTTPException(status_code=401, detail="Account deactivated")

            password_hash = current.password_hash
            verification = bcrypt.checkpw(data.password.encode('utf-8'), password_hash.encode('utf-8'))

            if not verification:
                raise HTTPException(status_code=401, detail="Invalid credentials")  

            
            user_data = {
                "sub": current.username,        
                "username": current.username,  
                "role": current.role.name,
                "level": current.level.name, 
                "user_id": current.id
            }
            
            access_token, refresh_token = create_tokens(user_data)
            set_auth_cookies(response, access_token, refresh_token)
            
            logger.info(f"User logged in: {current.username}")  
            return {"role": current.role, 
                 "username": current.username,
                 "user_id":current.id,
                 "district_id": current.district_id if current.district_id else None,
                 "district_name": current.district.name if current.district else None,
                 "local_body_id": current.local_body_id if current.local_body_id else None,
                 "local_body_name": current.local_body.name if current.local_body else None,
                 "warehouse_id": current.warehouse_id if current.warehouse_id else None,
                 "status" : "success"}
        
    except HTTPException:
        raise 
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post('/refresh')
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token"""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    try:
      
        payload = verify_refresh_token(refresh_token)
        
        
        with Database.get_session() as session:
            current = session.query(User).options(
                joinedload(User.role),
                joinedload(User.level)
            ).filter(User.id == payload["user_id"]).first()
            
            if not current or current.is_active is False:
                raise HTTPException(status_code=401, detail="User not found or deactivated")
            
            
            user_data = {
                "sub": current.username,
                "username": current.username,
                "role": current.role.name,
                "level": current.level.name, 
                "user_id": current.id
            }
        
     
        old_jti = payload["jti"]
        revoke_refresh_token(old_jti)
        
      
        new_access_token, new_refresh_token = create_tokens(user_data)
        set_auth_cookies(response, new_access_token, new_refresh_token)
        
        logger.info(f"Tokens refreshed for user: {payload.get('sub')}")
        return {"message": "Tokens refreshed"}
    
    except HTTPException:
        clear_auth_cookies(response)
        raise
    except Exception as e:
        logger.error(f"Refresh error: {str(e)}")
        clear_auth_cookies(response)
        raise HTTPException(status_code=500, detail="Token refresh failed")
    
@router.post('/logout')
async def logout(request: Request, response: Response, current_user: dict = Depends(get_current_user)):
    """Logout and revoke refresh token"""
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    
    if refresh_token:
        try:
           
            payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, [ALGORITHM], options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                revoke_refresh_token(jti)
        except:
            pass  
    
    clear_auth_cookies(response)
    logger.info(f"User logged out: {current_user.get('sub')}")
    return {"message": "Logged out"}

@router.post('/logout-all')
async def logout_all_devices(current_user: dict = Depends(get_current_user), response: Response = None):
    """Logout from all devices by revoking all refresh tokens for user"""
    user_id = current_user.get("user_id")
    
   
    tokens_to_revoke = [jti for jti in active_refresh_tokens]  
    for jti in tokens_to_revoke:
        revoke_refresh_token(jti)
    
    clear_auth_cookies(response)
    logger.info(f"User logged out from all devices: {current_user.get('sub')}")
    return {"message": "Logged out from all devices"}

@router.get('/me')
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
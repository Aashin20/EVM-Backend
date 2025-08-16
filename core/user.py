# from utils.authtoken import create_token, verify_token
from .db import Database
from models.users import User, LocalBody, District, LocalBodyType,Warehouse
from models.evm import PollingStation,PairingRecord,EVMComponent,EVMComponentType
import bcrypt
from pydantic import BaseModel, constr
from typing import Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func, cast, Integer
from typing import List
from fastapi import HTTPException, Response
from models.users import Role
from datetime import datetime
from zoneinfo import ZoneInfo
import traceback
from utils.authtoken import create_tokens

class RegisterModel(BaseModel):
    username: constr(strip_whitespace=True, min_length=3)
    password: constr(min_length=6)
    email: Optional[constr(strip_whitespace=True, min_length=3)] = None
    role_id: int
    level_id: int
    district_id: Optional[int] = None
    local_body_id: Optional[str] = None
    warehouse_id: Optional[int] = None

class UpdateUserModel(BaseModel):
    user_id: int
    username: Optional[constr(strip_whitespace=True, min_length=3)] = None
    password: Optional[constr(min_length=6)] = None
    email: Optional[constr(strip_whitespace=True)] = None
    is_active: Optional[constr(strip_whitespace=True)] = None
    
class LoginModel(BaseModel):
    username: constr(strip_whitespace=True, min_length=3)
    password: constr(min_length=6)

class PollingStationModel(BaseModel):
    name: str
    local_body_id: str


def register(details: RegisterModel):
    with Database.get_session() as session:
        existing_user = session.query(User).filter(User.username == details.username).first()
        if existing_user:
            raise HTTPException(status_code=409,detail="Username Already Exists")
        
        hashed_password = bcrypt.hashpw(details.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        local_body_id = details.local_body_id if details.local_body_id not in [0, "0"] else None
        warehouse_id = details.warehouse_id if details.warehouse_id not in [0, "0"] else None
        new_user = User(
            username=details.username,
            password_hash=hashed_password,
            email=details.email,
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
        email = new_user.email
        level_name = new_user.level.name
        user_id = new_user.id
        username = new_user.username

    token = create_tokens({
        "username": username,
        "role": role_name,
        "email": email,
        "level": level_name,
        "user_id": user_id
    })

    return {
        "token": token,
        "role": role_name,
        "level": level_name,
        "user_id": user_id
    }

def view_users():
    with Database.get_session() as session:
        users = session.query(User).all()
        if not users:
            raise HTTPException(status_code=404,detail="No users found")
        return [
            {
                "id": user.id,
                "name": user.username,
                "email" : user.email,
                "created_by": user.created_by.username if user.created_by else None,
                "updated_by": user.updated_by.username if user.updated_by else None,
                "updated_at": user.updated_at,
                "created_at": user.created_at,
                "status": "Active" if user.is_active else "Inactive",
                "role": user.role.name,
                "district_id": user.district_id,
                "local_body_id": user.local_body_id,
              
            } for user in users
        ]
    
def edit_user(details: UpdateUserModel):
    with Database.get_session() as session:
        user = session.query(User).filter(User.id == details.user_id).first()
        if not user:
            raise HTTPException(status_code=404,detail="User not found")
        
        if details.username:
            existing_user = session.query(User).filter(User.username == details.username, User.id != details.user_id).first()
            if existing_user:
                raise HTTPException(status_code=409,detail="Username already exists")
            user.username = details.username
        
        if details.password:
            user.password_hash = bcrypt.hashpw(details.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        if details.email:
            existing_email = session.query(User).filter(User.email == details.email, User.id != details.user_id).first()
            if existing_email:
                raise HTTPException(status_code=409,detail="Email Already Exists")
            user.email = details.email
        if details.is_active is not None:
            if details.is_active == "Inactive":
                user.is_active = False
            else:
                user.is_active = True
        user.updated_by_id = details.user_id
        
        #user.updated_by = get_current_user(user_id)
        session.commit()
        session.refresh(user)
        
        return Response(status_code=200)
    
def get_local_body(district_id: int,type: str):
    with Database.get_session() as session:
        local_body = session.query(LocalBody).filter(
            LocalBody.district_id == district_id,
            LocalBody.type == type
        ).all()
        
        if not local_body:
            raise HTTPException(status_code=204,detail="No local body found")
        
        return [
            {
                "id": lb.id,
                "name": lb.name,
                "users": [
                    {
                        "id": user.id,
                    } for user in lb.users
                ]
            } for lb in local_body
        ]
    

def get_districts():
    with Database.get_session() as session:
        districts = session.query(District).distinct().all()
        
        if not districts:
            raise HTTPException(status_code=204,detail="No district found")
        
        return [
            {
                "id": district.id,
                "name": district.name,
            } for district in districts
        ]
    
def get_panchayath(block_id: str):
    block = block_id[:5]
    with Database.get_session() as session:
        panchayath = session.query(LocalBody).filter(
            LocalBody.id.startswith(block),
            LocalBody.type == LocalBodyType.Grama_Panchayat
        ).all()
        if not panchayath:
            raise HTTPException(status_code=204,detail="No panchayaths found")
        return [
            {
                "id": lb.id,
                "name": lb.name,
                "users": [
                    {
                        "id": user.id,
                    } for user in lb.users
                ]
            } for lb in panchayath
        ]
    
def get_user(local_body_id: str):
    with Database.get_session() as session:
        user = session.query(User).filter(User.local_body_id == local_body_id).first()
        if not user:
            raise HTTPException(status_code=204,detail="No users found")
        
        return {
            "id": user.id,
            "username": user.username,
            "district_id": user.district_id,
            "local_body_id": user.local_body_id,
            "warehouse_id": user.warehouse_id
        }
    
def get_RO(local_body_id: str):
    local = local_body_id[:5]
    with Database.get_session() as session:
        panchayath = session.query(LocalBody).filter(
            LocalBody.id.like(f"{local}%"),
            or_(
                LocalBody.type == LocalBodyType.Corporation_RO.value,
                LocalBody.type == LocalBodyType.Municipality_RO.value
            )
        ).all()

        if not panchayath:
            raise HTTPException(status_code=204,detail="No RO found")

        return [
            {
                "id": lb.id,
                "name": lb.name,
                "users": [{"id": user.id} for user in lb.users]
            }
            for lb in panchayath
        ]


def add_ps(datas: List[PollingStationModel]):
    with Database.get_session() as session:
        for data in datas:
            local_body = session.query(LocalBody).filter(LocalBody.id == data.local_body_id).first()
            if not local_body:
                raise HTTPException(status_code=404, detail=f"Local body with ID {data.local_body_id} not found")   
            
            new_ps = PollingStation(name=data.name, status="pending",local_body_id=data.local_body_id)
            session.add(new_ps)
        
        session.commit()
        return Response(status_code=200)

def approve_ps(ps_ids: List[int], approver_id: int):
    with Database.get_session() as session:
        # Fetch polling stations
        polling_stations = session.query(PollingStation).filter(PollingStation.id.in_(ps_ids)).all()

        # Validate
        found_ids = {ps.id for ps in polling_stations}
        not_found = [ps_id for ps_id in ps_ids if ps_id not in found_ids]
        if not_found:
            raise HTTPException(status_code=404, detail=f"Polling stations not found: {not_found}")

        # Approve all
        for ps in polling_stations:
            ps.status = "approved"
            ps.approver_id = approver_id

        session.commit()
        return Response(status_code=200)
    
def reject_ps(ps_ids: List[int], approver_id: int):
    with Database.get_session() as session:
        polling_stations = session.query(PollingStation).filter(PollingStation.id.in_(ps_ids)).all()
        found_ids = {ps.id for ps in polling_stations}
        not_found = [ps_id for ps_id in ps_ids if ps_id not in found_ids]

        if not_found:
            raise HTTPException(status_code=404, detail=f"Polling stations not found: {not_found}")

        for ps in polling_stations:
            ps.status = "rejected"
            ps.approver_id = approver_id

        session.commit()
        return Response(status_code=200)

def view_ps(district_id: int):
    with Database.get_session() as session:
        polling_stations = (
            session.query(PollingStation,LocalBody.name)
            .join(LocalBody, PollingStation.local_body_id == LocalBody.id)
            .filter(LocalBody.district_id == district_id)
            .filter(PollingStation.status == "pending")
            .all()
        )

        grouped_data = {}
        for ps, local_body_name in polling_stations:
            if local_body_name not in grouped_data:
                grouped_data[local_body_name] = []
            
            grouped_data[local_body_name].append({
                "psname": ps.name,
                "ps_id": ps.id
            })

        return [grouped_data]

def get_ps(local_body:str):
    with Database.get_session() as session:
        polling_stations = (
            session.query(PollingStation)
            .filter(PollingStation.local_body_id == local_body)
            .filter(PollingStation.status == "approved")
            .all()
        )
        if not polling_stations:
            raise HTTPException(status_code=204)

        return [
            {
                "id": ps.id,
                "name": ps.name,
            }
            for ps in polling_stations
        ]

def get_evm_from_ps(local_body: str):
    with Database.get_session() as session:
        results = (
            session.query(PollingStation, PairingRecord)
            .outerjoin(PairingRecord, PairingRecord.polling_station_id == PollingStation.id)
            .filter(PollingStation.local_body_id == local_body)
            .filter(PollingStation.status == "approved")
            .all()
        )

        if not results:
            raise HTTPException(status_code=204)

        final_data = []
        for ps, pairing in results:
            components = {
                "cu": [],
                "dmm": [],
                "bu": [],
                "bu_pink_paper": [],
                "evm_id": []
            }

            if pairing:
                # Add evm_id as a list (even if it's a single value)
                if pairing.evm_id:
                    components["evm_id"].append(pairing.evm_id)

                evm_components = (
                    session.query(EVMComponent)
                    .filter(EVMComponent.pairing_id == pairing.id)
                    .all()
                )

                for comp in evm_components:
                    if comp.component_type == EVMComponentType.CU:
                        components["cu"].append(comp.serial_number)
                    elif comp.component_type == EVMComponentType.DMM:
                        components["dmm"].append(comp.serial_number)
                    elif comp.component_type == EVMComponentType.BU:
                        components["bu"].append(comp.serial_number)
                    elif comp.component_type == EVMComponentType.BU_PINK_PAPER_SEAL:
                        components["bu_pink_paper"].append(comp.serial_number)

            final_data.append({
                "ps_id": ps.id,
                "ps_name": ps.name,
                "components": components
            })

        return final_data

            
def mass_deactivate(role_name: str, user_id:int):
    with Database.get_session() as db:
        try:
            role = db.query(Role).filter(Role.name == role_name).first()
            
            active_users = db.query(User).filter(
                User.role_id == role.id,
            ).all()
            
            if not active_users:
                raise HTTPException(status_code=204,detail="No active users found")
            
            if active_users[0].is_active==True:
                status = False
            else:
                status = True
            for user in active_users:
                
                # Deactivate the user
                user.is_active = status
                user.updated_by_id = user_id
                user.updated_at = datetime.now(ZoneInfo("Asia/Kolkata"))
            
            db.commit()
            
            return Response(status_code=200)
            
        except Exception as e:
            db.rollback()
            return Response(status_code=400)

def get_warehouse(district: int):
    with Database.get_session() as db:
        warehouses = db.query(Warehouse).filter(Warehouse.district_id==district).all()

        return [{
            "id":ware.id,
            "name": ware.name,
        }for ware in warehouses]

def get_deo():
    with Database.get_session() as session:
        users = session.query(User).options(
            joinedload(User.district)
        ).filter(User.role_id == 2).all()
        if not users:
            raise HTTPException(status_code=204,detail="No users found")
        
        return [{
            "id": user.id,
            "name": user.district.name,
            "district_id": user.district_id,
        }for user in users]

def add_warehouse(dis_id: int, warehouse_name: str):
    with Database.get_session() as db:
        warehouse = db.query(Warehouse).filter(Warehouse.name == warehouse_name).all()
        if warehouse:
            raise HTTPException(status_code=409, detail="Warehouse name already exists")
        
        max_id = db.query(func.max(cast(Warehouse.id, Integer))).scalar()
        next_id = str((max_id or 0) + 1)
        
        new = Warehouse(
            id=next_id,
            name=warehouse_name,
            district_id=dis_id
        )
        db.add(new)
        db.commit()
        return Response(status_code=200)
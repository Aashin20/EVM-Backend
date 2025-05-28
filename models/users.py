from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from core.db import Base


class LevelEnum(str, enum.Enum):
    Developer = "Developer"
    State = "State"
    District = "District"
    Block_Panchayat = "Block Panchayat"
    Municipality = "Municipality"
    Corportation = "Corporation"
    Grama_Panchayat = "Grama Panchayat"

class LocalBodyType(str, enum.Enum):
    Grama_Panchayat  = "Grama Panchayat"
    Block_Panchayat = "Block Panchayat"
    Municipality = "Municipality"
    Corportation = "Corporation"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


    district_id = Column(Integer, ForeignKey('districts.id'), nullable=True)
    local_body_id = Column(Integer, ForeignKey('local_bodies.id'), nullable=True)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=True)

   
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    level_id = Column(Integer, ForeignKey('levels.id'), nullable=False)

 
    role = relationship("Role", back_populates="users")
    level = relationship("Level", back_populates="users")
    district = relationship("District", back_populates="users")
    local_body = relationship("LocalBody", back_populates="users")
    warehouse = relationship("Warehouse", back_populates="users")


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  

    users = relationship("User", back_populates="role")


class Level(Base):
    __tablename__ = 'levels'

    id = Column(Integer, primary_key=True)
    name = Column(Enum(LevelEnum), unique=True, nullable=False)
    hierarchy_order = Column(Integer, nullable=False)

    users = relationship("User", back_populates="level")

class District(Base):
    __tablename__ = 'districts'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", back_populates="district")
    local_bodies = relationship("LocalBody", back_populates="district")
    warehouses = relationship("Warehouse", back_populates="district")


from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from core.db import Base
from zoneinfo import ZoneInfo


class LevelEnum(str, enum.Enum):
    Developer = "Developer"
    State = "State"
    District = "District"
    Block_Panchayat = "Block_Panchayat"
    Municipality = "Municipality"
    Corporation = "Corporation"
    Grama_Panchayat = "Grama_Panchayat"

class LocalBodyType(str, enum.Enum):
    Grama_Panchayat = "Grama_Panchayat"
    Block_Panchayat = "Block_Panchayat"
    Municipality = "Municipality"
    Corporation = "Corporation"
    Municipality_RO = "Municipality_RO"
    Corporation_RO = "Corporation_RO"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")), onupdate=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        remote_side=[id],
        uselist=False,
        backref="created_users"
    )

    
    updated_by_id = Column(Integer, ForeignKey('users.id'))
    updated_by = relationship(
        "User",
        foreign_keys=[updated_by_id],
        remote_side=[id],
        uselist=False,
        backref="updated_users"
    )

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")), onupdate=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))


    district_id = Column(Integer, ForeignKey('districts.id'), nullable=True)
    local_body_id = Column(String, ForeignKey('local_bodies.id'), nullable=True)
    warehouse_id = Column(String, ForeignKey('warehouses.id'), nullable=True)

   
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

class Warehouse(Base):
    __tablename__ = 'warehouses'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String)
    district_id = Column(Integer, ForeignKey('districts.id'))

    district = relationship("District", back_populates="warehouses")
    users = relationship("User", back_populates="warehouse")


class LocalBody(Base):
    __tablename__ = 'local_bodies'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(LocalBodyType), nullable=False)
    district_id = Column(Integer, ForeignKey('districts.id'), nullable=False)
    district = relationship("District", back_populates="local_bodies")
    polling_stations = relationship("PollingStation", back_populates="local_body")
    users = relationship("User", back_populates="local_body")
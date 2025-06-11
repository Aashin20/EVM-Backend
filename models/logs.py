from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Enum, Date 
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from core.db import Base
from zoneinfo import ZoneInfo
from .evm import AllotmentType,ReturnReason,EVMComponentType
from .users import User

class AllotmentLogs(Base):
    __tablename__ = "allotment_logs"

    id = Column(Integer, primary_key=True)
    allotment_type = Column(Enum(AllotmentType), nullable=False)

    from_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    to_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    from_district_id = Column(Integer, ForeignKey('districts.id'), nullable=True)
    to_district_id = Column(Integer, ForeignKey('districts.id'), nullable=True)
    from_local_body_id = Column(String, ForeignKey('local_bodies.id'), nullable=True)
    to_local_body_id = Column(String, ForeignKey('local_bodies.id'), nullable=True)

    reject_reason = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    approved_at = Column(DateTime, nullable=True)

    is_temporary = Column(Boolean, default=False)
    temporary_reason = Column(String, nullable=True)

    # Relationships
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])
    from_district = relationship("District", foreign_keys=[from_district_id])
    to_district = relationship("District", foreign_keys=[to_district_id])
    from_local_body = relationship("LocalBody", foreign_keys=[from_local_body_id])
    to_local_body = relationship("LocalBody", foreign_keys=[to_local_body_id])

    items = relationship("AllotmentItemLogs", back_populates="allotment", cascade="all, delete-orphan")


class AllotmentItemLogs(Base):
    __tablename__ = 'allotment_items_logs'

    id = Column(Integer, primary_key=True)
    allotment_id = Column(Integer, ForeignKey('allotment_logs.id'))
    evm_component_id = Column(Integer, ForeignKey('evm_components_logs.id'))

    remarks = Column(String)

    allotment = relationship("AllotmentLogs", back_populates="items")
    evm_component = relationship("EVMComponentLogs")


class EVMComponentLogs(Base):
    __tablename__ = 'evm_components_logs'

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, nullable=False)  # Removed unique=True
    component_type = Column(Enum(EVMComponentType), nullable=False)

    status = Column(String, default="FLC_Pending")  
    is_verified = Column(Boolean, default=False)
    dom = Column(Date, nullable=True)
    box_no = Column(Integer, nullable=True)
    current_user_id = Column(Integer, ForeignKey('users.id'))
    created_on = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    current_warehouse_id = Column(String, ForeignKey('warehouses.id'), nullable=True)
    pairing_id = Column(Integer, ForeignKey('pairing_logs.id', ondelete="CASCADE"), nullable=True)
    pairing = relationship("PairingRecordLogs", back_populates="components")

    current_user = relationship("User")
    current_warehouse = relationship("Warehouse")


from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Enum, Date 
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from core.db import Base
from zoneinfo import ZoneInfo

class EVMComponentType(str, enum.Enum):
    CU = "CU"
    BU = "BU"
    DMM = "DMM"
    DMM_SEAL = "DMM_SEAL"
    PINK_PAPER_SEAL = "PINK_PAPER_SEAL"

class ReturnReason(str, enum.Enum):
    Polling_Completed = "Polling Completed"
    FLC_Failed = "FLC_Failed"
    Faulty = "Faulty/Damaged"
    Other = "Other"

class AllotmentType(str, enum.Enum):
    SEC_TO_DEO = "SEC_TO_DEO"       
    DEO_TO_DEO = "DEO_TO_DEO"       
    DEO_TO_BO = "DEO_TO_BO"         
    BO_TO_RO = "BO_TO_RO"           
    DEO_TO_ERO = "DEO_TO_ERO"
    ERO_TO_RO = "ERO_TO_RO"
    RO_TO_BO = "RO_TO_BO"
    RO_TO_ERO = "RO_TO_ERO"
    BO_TO_DEO = "BO_TO_DEO"
    ERO_TO_DEO = "ERO_TO_DEO"
    DEO_TO_SEC = "DEO_TO_SEC"

class NotificationType(str, enum.Enum):
    NEW_EVM_ALLOTMENT = "New EVM Allotment"
    RETURN_REQUEST = "Return Request"
    FLC_PENDING = "FLC Pending"
    OTHER = "Other"

class EVMComponent(Base):
    __tablename__ = 'evm_components'

    id = Column(Integer, primary_key=True)
    serial_number = Column(String, unique=True, nullable=False)
    component_type = Column(Enum(EVMComponentType), nullable=False)

    status = Column(String, default="FLC_Pending")  # available, paired, used, failed, returned
    is_allocated = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    dom = Column(Date, nullable=True)
    box_no = Column(Integer, nullable=True)
    current_user_id = Column(Integer, ForeignKey('users.id'))
    current_warehouse_id = Column(String, ForeignKey('warehouses.id'), nullable=True)
    pairing_id = Column(Integer, ForeignKey('pairings.id', ondelete="CASCADE"), nullable=True)
    pairing = relationship("PairingRecord", back_populates="components")

    current_user = relationship("User")
    current_warehouse = relationship("Warehouse")

class PairingRecord(Base):
    __tablename__ = 'pairings'

    id = Column(Integer, primary_key=True)
    evm_id = Column(String(50), unique=True, nullable=True,default=None)
    polling_station_id = Column(Integer, ForeignKey('polling_stations.id'), nullable=True)

    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    
    completed_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
     
    polling_station = relationship("PollingStation", back_populates="pairing_records")
    created_by = relationship("User", foreign_keys=[created_by_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    components = relationship("EVMComponent", back_populates="pairing")

class Allotment(Base):
    __tablename__ = "allotments"

    id = Column(Integer, primary_key=True)
    allotment_type = Column(Enum(AllotmentType), nullable=False)

    from_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    to_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    from_district_id = Column(Integer, ForeignKey('districts.id'), nullable=True)
    to_district_id = Column(Integer, ForeignKey('districts.id'), nullable=True)
    from_local_body_id = Column(String, ForeignKey('local_bodies.id'), nullable=True)
    to_local_body_id = Column(String, ForeignKey('local_bodies.id'), nullable=True)

    initiated_by_id = Column(Integer, ForeignKey('users.id'))
    approved_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    is_return = Column(Boolean, default=False)
    return_reason = Column(Enum(ReturnReason), nullable=True)
    original_allotment_id = Column(Integer, ForeignKey('allotments.id'), nullable=True)

    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    approved_at = Column(DateTime, nullable=True)

    is_temporary = Column(Boolean, default=False)
    temporary_reason= Column(String, nullable=True)

    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])
    initiated_by = relationship("User", foreign_keys=[initiated_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    from_district = relationship("District", foreign_keys=[from_district_id])
    to_district = relationship("District", foreign_keys=[to_district_id])
    from_local_body = relationship("LocalBody", foreign_keys=[from_local_body_id])
    to_local_body = relationship("LocalBody", foreign_keys=[to_local_body_id])

    items = relationship("AllotmentItem", back_populates="allotment", cascade="all, delete-orphan")
    original_allotment = relationship("Allotment", remote_side=[id])


class AllotmentItem(Base):
    __tablename__ = 'allotment_items'

    id = Column(Integer, primary_key=True)
    allotment_id = Column(Integer, ForeignKey('allotments.id'))
    evm_component_id = Column(Integer, ForeignKey('evm_components.id'))

    remarks = Column(String)

    allotment = relationship("Allotment", back_populates="items")
    evm_component = relationship("EVMComponent")


class FLCRecord(Base):
    __tablename__ = 'flc_records'

    id = Column(Integer, primary_key=True)
    cu_id = Column(Integer, ForeignKey('evm_components.id'), nullable=False)
    dmm_id = Column(Integer, ForeignKey('evm_components.id'), nullable=False)
    dmm_seal_id = Column(Integer, ForeignKey('evm_components.id'), nullable=False)         
    pink_paper_seal_id = Column(Integer, ForeignKey('evm_components.id'), nullable=False) 


    box_no = Column(String)
   

    passed = Column(Boolean, default=False)
    remarks = Column(String, nullable=True)

    flc_by_id = Column(Integer, ForeignKey('users.id'))
    flc_date = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    cu = relationship("EVMComponent", foreign_keys=[cu_id])
    dmm = relationship("EVMComponent", foreign_keys=[dmm_id])
    flc_by = relationship("User")
    dmm_seal = relationship("EVMComponent", foreign_keys=[dmm_seal_id])            
    pink_paper_seal = relationship("EVMComponent", foreign_keys=[pink_paper_seal_id])


class FLCBallotUnit(Base):
    __tablename__ = 'flc_bu'

    id = Column(Integer, primary_key=True)
    bu_id = Column(Integer, ForeignKey('evm_components.id'))
    box_no = Column(String)
    passed = Column(Boolean, default=False)
    remarks = Column(String)
    flc_by_id = Column(Integer, ForeignKey('users.id'))
    flc_date = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))
    flc_by = relationship("User")
    bu = relationship("EVMComponent")



class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(Enum(NotificationType), nullable=False)
    message = Column(String)
    target_table = Column(String)
    target_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    user = relationship("User")

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String)
    table = Column(String)
    record_id = Column(Integer)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    user = relationship("User")

class PollingStation(Base):
        __tablename__ = 'polling_stations'
        
        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        local_body_id = Column(String, ForeignKey('local_bodies.id'), nullable=False)
        status = Column(String, nullable=True)  
        approver_id = Column(Integer, ForeignKey('users.id'), nullable=True)
        local_body = relationship("LocalBody", back_populates="polling_stations")
        pairing_records = relationship("PairingRecord", back_populates="polling_station")
        approver = relationship("User", foreign_keys=[approver_id])
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Enum
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
    SEC_TO_DEO = "SEC to DEO"
    DEO_TO_BO = "DEO to Block Officer"
    BO_TO_RO = "BO to Returning Officer"
    RO_TO_PO = "RO to Presiding Officer"
    RETURN = "Return"


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

    status = Column(String, default="available")  # available, paired, used, failed, returned
    is_allocated = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    current_user_id = Column(Integer, ForeignKey('users.id'))
    current_warehouse_id = Column(Integer, ForeignKey('warehouses.id'), nullable=True)

    current_user = relationship("User")
    current_warehouse = relationship("Warehouse")


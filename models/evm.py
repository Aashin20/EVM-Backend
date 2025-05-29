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


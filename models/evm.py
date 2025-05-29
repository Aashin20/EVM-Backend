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

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


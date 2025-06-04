from core.db import Database
from models.evm import FLCRecord, FLCBallotUnit, EVMComponentType, EVMComponent,PairingRecord
from pydantic import BaseModel
from fastapi import HTTPException
from typing import Optional, List
from fastapi import Response


class FLCCUModel(BaseModel):
    cu_serial: str
    dmm_serial: str
    dmm_seal_serial: str
    pink_paper_seal_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None
    flc_by_id: int

class FLCBUModel(BaseModel):
    bu_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None
    flc_by_id: int




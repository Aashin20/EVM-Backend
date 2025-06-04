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







def flc_bu(datas: list[FLCBUModel]):
    with Database.get_session() as session:
        for data in datas:
            bu = session.query(EVMComponent).filter_by(serial_number=data.bu_serial).first()
            if not all([bu]):
                raise HTTPException(status_code=404, detail=data.bu_serial)
            
            flc = FLCBallotUnit(
                bu_id=bu.id,
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=data.flc_by_id
            )
            session.add(flc)
            if data.passed:
                bu.status = "FLC_Passed"
            else:
                bu.status = "FLC_Failed"
        session.commit()
    return 200
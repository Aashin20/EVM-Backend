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
    

class FLCBUModel(BaseModel):
    bu_serial: str
    box_no: str
    passed: bool
    remarks: Optional[str] = None
    flc_by_id: int



def flc_cu(data_list: List[FLCCUModel],user_id: int):
    with Database.get_session() as session:
        for data in data_list:
            cu = session.query(EVMComponent).filter_by(serial_number=data.cu_serial).first()
            dmm = session.query(EVMComponent).filter_by(serial_number=data.dmm_serial).first()

            if not all([cu, dmm]):
                raise HTTPException(status_code=404, detail=f"CU or DMM not found for CU serial {data.cu_serial} or DMM serial {data.dmm_serial}")

            if cu.component_type != EVMComponentType.CU or dmm.component_type != EVMComponentType.DMM:
                raise HTTPException(status_code=400, detail=f"Component types are incorrect for CU serial {data.cu_serial} or DMM serial {data.dmm_serial}")

            dmm_seal = session.query(EVMComponent).filter_by(serial_number=data.dmm_seal_serial).first()
            if not dmm_seal:
                dmm_seal = EVMComponent(
                    serial_number=data.dmm_seal_serial,
                    component_type=EVMComponentType.DMM_SEAL,
                    status="FLC_Passed" if data.passed else "FLC_Failed",
                    is_verified=True,
                    box_no=data.box_no
                )
                session.add(dmm_seal)
                session.flush()

            pink_paper_seal = session.query(EVMComponent).filter_by(serial_number=data.pink_paper_seal_serial).first()
            if not pink_paper_seal:
                pink_paper_seal = EVMComponent(
                    serial_number=data.pink_paper_seal_serial,
                    component_type=EVMComponentType.PINK_PAPER_SEAL,
                    status="FLC_Passed" if data.passed else "FLC_Failed",
                    is_verified=True,
                    box_no=data.box_no
                )
                session.add(pink_paper_seal)
                session.flush()

            flc = FLCRecord(
                cu_id=cu.id,
                dmm_id=dmm.id,
                dmm_seal_id=dmm_seal.id,
                pink_paper_seal_id=pink_paper_seal.id,
                box_no=data.box_no,
                passed=data.passed,
                remarks=data.remarks,
                flc_by_id=user_id
            )
            session.add(flc)
            pairing = PairingRecord(created_by_id=user_id)
            session.add(pairing)
            session.flush()

            cu.pairing_id = pairing.id
            cu.box_no = data.box_no
            dmm.box_no = data.box_no
            dmm.pairing_id = pairing.id
            dmm_seal.pairing_id = pairing.id
            pink_paper_seal.pairing_id = pairing.id
            if data.passed:
                cu.status = "FLC_Passed"
                dmm.status = "FLC_Passed"
            else:
                cu.status = "FLC_Failed"
                dmm.status = "FLC_Failed"

        session.commit()
    return Response(status_code=200)



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
            bu.box_no = data.box_no
            if data.passed:
                bu.status = "FLC_Passed"
            else:
                bu.status = "FLC_Failed"
        session.commit()
    return 200
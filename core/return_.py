from typing import List
from core.db import Database
from models.evm import EVMComponent, PairingRecord,PollingStation,FLCRecord,FLCBallotUnit
from fastapi import Response,HTTPException

def status_change(local_body: str,status: str):
    if status not in ["polling","polled","counted"]:
        raise HTTPException(status_code=204)
    elif status == "polling":
        current_status = "commissioned"
    elif status == "polled":
        current_status = "polling"
    elif status == "counted":
        current_status = "polled"
    with Database.get_session() as session:
        evm_components = (
            session.query(EVMComponent)
            .join(PairingRecord, EVMComponent.pairing_id == PairingRecord.id)
            .join(PollingStation, PairingRecord.polling_station_id == PollingStation.id)
            .filter(PollingStation.local_body_id == local_body)
            .filter(PollingStation.status == "approved")
            .filter(EVMComponent.status == current_status)
        )
        
        for component in evm_components:
            component.status = status
        
        session.commit()
        return Response(status_code=200)

def decommission_evms(local_body_id: str, evm_ids: List[str]):
    with Database.get_session() as session:
        try:
            # Get all pairings
            pairings = (
                session.query(PairingRecord)
                .join(PollingStation)
                .filter(PollingStation.local_body_id == local_body_id)
                .filter(PairingRecord.evm_id.in_(evm_ids))
                .all()
            )
            
            if not pairings:
                raise HTTPException(status_code=404, detail="No EVMs found")
            
            if len(pairings) != len(evm_ids):
                raise HTTPException(status_code=404, detail="Some EVMs not found")
            
            # First validate ALL EVMs are eligible
            for pairing in pairings:
                cu = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id,
                    EVMComponent.component_type == "CU"
                ).first()
                
                dmm = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id,
                    EVMComponent.component_type == "DMM"
                ).first()
                
                if not (cu and cu.status == "counted" and dmm and dmm.status == "counted"):
                    raise HTTPException(status_code=400, detail=f"EVM {pairing.evm_id} not eligible")
            
            # First delete related FLC records to avoid foreign key violations
            for pairing in pairings:
                components = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id
                ).all()
                
                for comp in components:
                    # Delete any FLC records that reference this component
                    if comp.component_type == "DMM_SEAL":
                        session.query(FLCRecord).filter(
                            FLCRecord.dmm_seal_id == comp.id
                        ).delete(synchronize_session=False)
                    elif comp.component_type == "PINK_PAPER_SEAL":
                        session.query(FLCRecord).filter(
                            FLCRecord.pink_paper_seal_id == comp.id
                        ).delete(synchronize_session=False)
                    elif comp.component_type == "DMM":
                        session.query(FLCRecord).filter(
                            FLCRecord.dmm_id == comp.id
                        ).delete(synchronize_session=False)
                    elif comp.component_type == "CU":
                        session.query(FLCRecord).filter(
                            FLCRecord.cu_id == comp.id
                        ).delete(synchronize_session=False)
                    elif comp.component_type == "BU":
                        session.query(FLCBallotUnit).filter(
                            FLCBallotUnit.bu_id == comp.id
                        ).delete(synchronize_session=False)
            
            # Now handle components and pairings
            for pairing in pairings:
                components = session.query(EVMComponent).filter(
                    EVMComponent.pairing_id == pairing.id
                ).all()
                
                for comp in components:
                    if comp.component_type in ["DMM_SEAL", "PINK_PAPER_SEAL"]:
                        session.delete(comp)
                    elif comp.component_type == "DMM":
                        comp.status = "treasury"
                        comp.pairing_id = None
                    else:
                        comp.status = "FLC_Pending"
                        comp.pairing_id = None
                
                session.delete(pairing)
            
            session.commit()
            return Response(status_code=200)
            
        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(e))
from typing import List
from core.db import Database
from models.evm import EVMComponent, PairingRecord,PollingStation
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
from core.db import Database
from models.evm import FLCRecord, FLCBallotUnit, EVMComponentType, EVMComponent,PairingRecord
from pydantic import BaseModel
from fastapi import HTTPException
from typing import Optional, List
from fastapi import Response



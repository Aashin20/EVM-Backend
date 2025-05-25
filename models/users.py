from sqlalchemy import Column, Integer, String, Boolean
from core.db import Base

class User(Base):
    
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  
    is_active = Column(Boolean, default=True)
    created_at = Column(Integer, nullable=False)

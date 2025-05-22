from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

class Database:
    _engine = None
    _SessionLocal = None
    Base = declarative_base()

    @classmethod
    def initialize(cls):
        if not cls._engine:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                raise ValueError("DATABASE_URL not set in environment.")
            cls._engine = create_engine(db_url)
            cls._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls._engine)
            return True
        return False
    
    @classmethod
    def get_db(cls):
        if not cls._SessionLocal:
            cls.initialize()
        db = cls._SessionLocal()
        try:
            yield db
        finally:
            db.close()
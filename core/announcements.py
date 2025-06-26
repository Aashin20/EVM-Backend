from models.alert import Announcements
from core.db import Database
from fastapi import Response,HTTPException

def create_announcement(content: str,from_user_id: int,to_user:str):
    try:
        with Database().get_session() as db:
            announcement = Announcements(content = content, from_user_id=from_user_id, to_user=to_user)
            db.add(announcement)
            db.commit()
        return Response(status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating announcement: {str(e)}")
    

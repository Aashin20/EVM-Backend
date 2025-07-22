from models.alert import Announcements
from core.db import Database
from fastapi import Response,HTTPException

def create_announcement(title:str,content: str,tag:str,from_user_id: int,to_user:str):
    try:
        with Database().get_session() as db:
            announcement = Announcements(title=title,content = content, tag=tag, from_user_id=from_user_id, to_user=to_user)
            db.add(announcement)
            db.commit()
        return Response(status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating announcement: {str(e)}")
    
def view_announcements(user_id: int,role: str):
    try:
        user_id = str(user_id)
        with Database().get_session() as db:
            announcements=db.query(Announcements).filter(
                (Announcements.to_user == user_id) | 
                (Announcements.to_user == role) | 
                (Announcements.to_user == "All")
            ).all()
            if not announcements:
                raise HTTPException(status_code=200, detail="No announcements found")
            return announcements
    except HTTPException:
        raise  
    except Exception as e:
        print(f"Error fetching announcements: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from app.database import get_db
from app.utils import decode_token

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("/")
def get_notifications(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    rows = db.execute("""
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (user_id,)).fetchall()
    
    return {"notifications": [dict(r) for r in rows]}

@router.post("/read-all")
def mark_all_as_read(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    db.commit()
    return {"message": "All notifications marked as read"}

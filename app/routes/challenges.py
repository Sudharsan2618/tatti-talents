from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import sqlite3
import json
import os
import shutil
from typing import Optional
from app.database import get_db, UPLOAD_DIR
from app.utils import decode_token

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

def _require_hr(token: str):
    payload = decode_token(token)
    if not payload or payload.get("role") not in ("hr", "admin"):
        raise HTTPException(401, "HR login required.")
    return payload

def _require_admin(token: str):
    payload = decode_token(token)
    if not payload or payload.get("role") != "admin" and payload.get("sub") != "admin@tatti.in":
        raise HTTPException(401, "Admin login required.")
    return payload

def _require_student(token: str):
    payload = decode_token(token)
    if not payload or payload.get("role") != "student":
        raise HTTPException(401, "Student login required.")
    return payload

class ChallengeCreate(BaseModel):
    token: str
    title: str
    description: str
    deadline: str
    skills: list[str] = []

@router.post("/")
def create_challenge(data: ChallengeCreate, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(data.token)
    hr_id = payload.get("uid")

    cur = db.execute("""
        INSERT INTO challenges (
            hr_id, title, description, deadline, skills
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        hr_id, data.title, data.description, data.deadline, json.dumps(data.skills)
    ))
    db.commit()
    return {"id": cur.lastrowid, "message": "Challenge created successfully!"}


@router.get("/")
def list_challenges(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("""
        SELECT c.*, h.company, h.name as hr_name
        FROM challenges c
        JOIN hr_users h ON c.hr_id = h.id
        ORDER BY c.created_at DESC
    """).fetchall()
    
    challenges = []
    for r in rows:
        d = dict(r)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        challenges.append(d)
    return {"challenges": challenges}


class SubmissionCreate(BaseModel):
    token: str
    upload_url: str

@router.post("/{challenge_id}/submit")
def submit_challenge(challenge_id: int, data: SubmissionCreate, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_student(data.token)
    student_id = payload.get("uid")
    
    existing = db.execute("SELECT id FROM submissions WHERE challenge_id = ? AND student_id = ?", (challenge_id, student_id)).fetchone()
    if existing:
        raise HTTPException(400, "You have already submitted for this challenge.")

    cur = db.execute("""
        INSERT INTO submissions (
            challenge_id, student_id, upload_url, status
        ) VALUES (?, ?, ?, 'pending')
    """, (
        challenge_id, student_id, data.upload_url
    ))
    db.commit()
    return {"id": cur.lastrowid, "message": "Submission sent successfully!"}


@router.post("/{challenge_id}/submit_file")
async def submit_challenge_file(challenge_id: int, file: UploadFile = File(...), token: str = Form(...), db: sqlite3.Connection = Depends(get_db)):
    payload = _require_student(token)
    student_id = payload.get("uid")
    
    existing = db.execute("SELECT id FROM submissions WHERE challenge_id = ? AND student_id = ?", (challenge_id, student_id)).fetchone()
    if existing:
        raise HTTPException(400, "You have already submitted for this challenge.")

    ext = os.path.splitext(file.filename)[1]
    filename = f"submission_{challenge_id}_{student_id}{ext}"
    path = UPLOAD_DIR / filename
    
    with open(str(path), "wb") as f:
        shutil.copyfileobj(file.file, f)

    upload_url = f"/uploads/{filename}"

    cur = db.execute("""
        INSERT INTO submissions (
            challenge_id, student_id, upload_url, status
        ) VALUES (?, ?, ?, 'pending')
    """, (
        challenge_id, student_id, upload_url
    ))
    db.commit()
    return {"id": cur.lastrowid, "message": "File submitted successfully!", "upload_url": upload_url}


@router.get("/{challenge_id}/submissions")
def get_challenge_submissions(challenge_id: int, token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(token)
    hr_id = payload.get("uid")

    challenge = db.execute("SELECT hr_id FROM challenges WHERE id = ?", (challenge_id,)).fetchone()
    if not challenge:
        raise HTTPException(404, "Challenge not found.")
    
    if challenge["hr_id"] != hr_id and payload.get("role") != "admin":
        raise HTTPException(403, "You can only view submissions for your own challenges.")

    rows = db.execute("""
        SELECT s.*, u.name as student_name, u.email as student_email
        FROM submissions s
        JOIN users u ON s.student_id = u.id
        WHERE s.challenge_id = ?
        ORDER BY s.created_at DESC
    """, (challenge_id,)).fetchall()
    
    return {"submissions": [dict(r) for r in rows]}


class ReviewAction(BaseModel):
    token: str
    status: str

@router.post("/submissions/{submission_id}/review")
def review_submission(submission_id: int, data: ReviewAction, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(data.token)
    
    if data.status not in ["selected", "rejected"]:
        raise HTTPException(400, "Invalid status.")

    submission = db.execute("""
        SELECT s.id, c.hr_id 
        FROM submissions s 
        JOIN challenges c ON s.challenge_id = c.id 
        WHERE s.id = ?
    """, (submission_id,)).fetchone()

    if not submission:
        raise HTTPException(404, "Submission not found.")
        
    if submission["hr_id"] != payload.get("uid") and payload.get("role") != "admin":
        raise HTTPException(403, "You can only review submissions for your own challenges.")

    db.execute("UPDATE submissions SET status = ? WHERE id = ?", (data.status, submission_id))
    db.commit()
    
    return {"message": f"Submission marked as {data.status}."}


@router.get("/all_submissions")
def get_all_submissions(token: str, db: sqlite3.Connection = Depends(get_db)):
    _require_admin(token)
    
    rows = db.execute("""
        SELECT s.*, u.name as student_name, u.email as student_email, c.title as challenge_title, h.company as hr_company
        FROM submissions s
        JOIN users u ON s.student_id = u.id
        JOIN challenges c ON s.challenge_id = c.id
        JOIN hr_users h ON c.hr_id = h.id
        ORDER BY s.created_at DESC
    """).fetchall()
    
    return {"submissions": [dict(r) for r in rows]}


class AdminReview(BaseModel):
    token: str
    rating: int
    feedback: str

@router.post("/submissions/{submission_id}/admin_review")
def admin_review_submission(submission_id: int, data: AdminReview, db: sqlite3.Connection = Depends(get_db)):
    _require_admin(data.token)
    
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(400, "Rating must be between 1 and 5.")

    db.execute("UPDATE submissions SET rating = ?, feedback = ? WHERE id = ?", (data.rating, data.feedback, submission_id))
    db.commit()
    
    return {"message": "Admin review saved successfully."}


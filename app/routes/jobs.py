from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
import json
from app.database import get_db
from app.utils import decode_token

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

from typing import List, Optional

class JobCreate(BaseModel):
    title: str
    company: str
    location: str = "Remote"
    salary: str = "Competitive"
    type: str = "Full-time"
    description: str
    requirements: List[str] = []
    skills_needed: List[str] = []

class ApplyJob(BaseModel):
    token: str
    job_id: int
    cover_letter: str = ""

@router.get("/")
def list_jobs(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM jobs WHERE status = 'open' ORDER BY created_at DESC").fetchall()
    jobs = []
    for r in rows:
        d = dict(r)
        d["requirements"] = json.loads(d["requirements"])
        d["skills_needed"] = json.loads(d["skills_needed"])
        jobs.append(d)
    return {"jobs": jobs}

@router.get("/my-applications")
def get_my_applications(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload: raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    rows = db.execute("""
        SELECT ja.*, j.title, j.company, j.location 
        FROM job_applications ja
        JOIN jobs j ON ja.job_id = j.id
        WHERE ja.student_id = ?
        ORDER BY applied_at DESC
    """, (user_id,)).fetchall()
    
    return {"applications": [dict(r) for r in rows]}

@router.post("/apply")
def apply_to_job(data: ApplyJob, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(data.token)
    if not payload: raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    # Check if already applied
    existing = db.execute("SELECT id FROM job_applications WHERE job_id = ? AND student_id = ?", (data.job_id, user_id)).fetchone()
    if existing: raise HTTPException(400, "Already applied to this job.")
    
    db.execute("""
        INSERT INTO job_applications (job_id, student_id, cover_letter)
        VALUES (?, ?, ?)
    """, (data.job_id, user_id, data.cover_letter))
    db.commit()
    
    return {"message": "Application submitted successfully!"}

@router.post("/bookmark")
def toggle_bookmark(token: str, job_id: int, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload: raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    existing = db.execute("SELECT id FROM bookmarks WHERE user_id = ? AND job_id = ?", (user_id, job_id)).fetchone()
    
    if existing:
        db.execute("DELETE FROM bookmarks WHERE user_id = ? AND job_id = ?", (user_id, job_id))
        db.commit()
        return {"message": "Bookmark removed."}
    else:
        db.execute("INSERT INTO bookmarks (user_id, job_id) VALUES (?, ?)", (user_id, job_id))
        db.commit()
        return {"message": "Job bookmarked."}

@router.get("/bookmarks")
def get_bookmarks(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload: raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    rows = db.execute("""
        SELECT j.* FROM jobs j
        JOIN bookmarks b ON j.id = b.job_id
        WHERE b.user_id = ?
    """, (user_id,)).fetchall()
    
    return {"bookmarks": [dict(r) for r in rows]}
@router.post("/")
def create_job(data: JobCreate, token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("role") != "hr":
        raise HTTPException(401, "Only HR can post jobs")
    
    hr_id = payload.get("uid")
    db.execute("""
        INSERT INTO jobs (hr_id, title, company, location, salary, type, description, requirements, skills_needed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (hr_id, data.title, data.company, data.location, data.salary, data.type, 
          data.description, json.dumps(data.requirements), json.dumps(data.skills_needed)))
    db.commit()
    return {"message": "Job posted successfully!"}

@router.get("/hr/my")
def get_hr_jobs(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("role") != "hr":
        raise HTTPException(401, "Unauthorized")
    
    hr_id = payload.get("uid")
    rows = db.execute("SELECT * FROM jobs WHERE hr_id = ? ORDER BY created_at DESC", (hr_id,)).fetchall()
    return {"jobs": [dict(r) for r in rows]}

@router.delete("/{job_id}")
def delete_job(job_id: int, token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("role") != "hr":
        raise HTTPException(401, "Unauthorized")
    
    hr_id = payload.get("uid")
    # Verify ownership
    existing = db.execute("SELECT id FROM jobs WHERE id = ? AND hr_id = ?", (job_id, hr_id)).fetchone()
    if not existing: raise HTTPException(404, "Job not found or unauthorized")
    
    db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    db.commit()
    return {"message": "Job deleted"}

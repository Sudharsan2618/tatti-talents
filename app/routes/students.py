"""
Student project CRUD routes.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import sqlite3
import json
import os
import shutil
from typing import Optional
from app.database import get_db, UPLOAD_DIR
from app.utils import decode_token

router = APIRouter(prefix="/api/students", tags=["students"])


@router.get("/")
def list_students(token: str = None, db: sqlite3.Connection = Depends(get_db)):
    """Get all students with their projects (redacted for guests/unapproved HR)."""
    # 1. Determine if the user is authorized for full details
    is_authorized = False
    if token:
        payload = decode_token(token)
        if payload:
            role = (payload.get("role") or "").lower()
            # Admins always have access
            # HR has access only if their account is approved
            email = payload.get("sub")
            is_admin = email == "admin@tatti.in" or role == "admin"
            
            is_approved_hr = False
            if role == "hr":
                res = db.execute("SELECT approved FROM hr_users WHERE email=?", (email,)).fetchone()
                if res and res[0]:
                    is_approved_hr = True
            
            if is_admin or is_approved_hr:
                is_authorized = True

    rows = db.execute("""
        SELECT id, name, email, phone, college, degree, year, linkedin,
               availability, jobrole, city, tatti_course, stipend,
               status, domain, ptitle, pdesc, impact, skills,
               github, demo, video, resume_path, tatti_certified, is_new, submitted_at
        FROM students
        WHERE ptitle IS NOT NULL AND ptitle != ''
          AND pdesc IS NOT NULL AND pdesc != ''
          AND LOWER(ptitle) != 'my profile'
          AND LOWER(pdesc) != 'welcome to your professional profile. add your projects and skills to get noticed!'
        ORDER BY submitted_at DESC
    """).fetchall()

    students = []
    for r in rows:
        d = dict(r)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        d["tatti_certified"] = bool(d["tatti_certified"])
        d["is_new"] = bool(d["is_new"])
        # has_resume: true if dedicated column set OR resume uploaded OR drive link present
        d["has_resume"] = bool(d.get("resume_path") or d.get("github"))
        
        # Privacy Redaction: Hide contact details and links if guest or student
        if not is_authorized:
            for field in ["email", "phone", "linkedin", "github", "demo", "video", "resume_path"]:
                d[field] = None

        students.append(d)
    return {"students": students, "total": len(students)}


@router.get("/me")
def get_my_profile(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    row = db.execute("SELECT * FROM students WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 1", (user_id,)).fetchone()
    
    if not row:
        db.execute("""
            INSERT INTO students (user_id, name, email, ptitle, pdesc, demo)
            VALUES (?, ?, ?, 'My Profile', 'Welcome to your professional profile. Add your projects and skills to get noticed!', '')
        """, (user_id, payload.get("name"), payload.get("sub")))
        db.commit()
        try:
            db.execute("""
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, 'Welcome to TalentAtlas!', 'Your profile has been initialized. Start exploring jobs and completing your profile.', 'info')
            """, (user_id,))
            db.commit()
        except Exception:
            pass  # Non-critical — don't let this block login
        row = db.execute("SELECT * FROM students WHERE user_id = ?", (user_id,)).fetchone()


    d = dict(row)
    d["skills"] = json.loads(d["skills"]) if d["skills"] else []
    d["tatti_certified"] = bool(d["tatti_certified"])
    d["is_new"] = bool(d["is_new"])
    d["has_resume"] = bool(d["resume_path"])
    return d


@router.get("/{student_id}")
def get_student(student_id: int, token: str = None, db: sqlite3.Connection = Depends(get_db)):
    # Authorization logic
    is_authorized = False
    if token:
        payload = decode_token(token)
        if payload:
            role = (payload.get("role") or "").lower()
            email = payload.get("sub")
            is_admin = email == "admin@tatti.in" or role == "admin"
            is_approved_hr = False
            if role == "hr":
                res = db.execute("SELECT approved FROM hr_users WHERE email=?", (email,)).fetchone()
                if res and res[0]: is_approved_hr = True
            if is_admin or is_approved_hr: is_authorized = True

    row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Student not found.")
    d = dict(row)
    d["skills"] = json.loads(d["skills"]) if d["skills"] else []
    d["tatti_certified"] = bool(d["tatti_certified"])
    d["is_new"] = bool(d["is_new"])
    d["has_resume"] = bool(d["resume_path"])
    
    if not is_authorized:
        for field in ["email", "phone", "linkedin", "github", "demo", "video", "resume_path"]:
            d[field] = None
    return d


class ProjectSubmit(BaseModel):
    token: str
    name: str
    email: str
    phone: str
    college: str
    degree: str = ""
    year: str = ""
    linkedin: str = ""
    availability: str = ""
    jobrole: str = ""
    city: str = ""
    tatti_course: str = ""
    stipend: str = ""
    domain: str = "other"
    ptitle: str
    pdesc: str
    impact: str = ""
    skills: list[str] = []
    github: str = ""
    demo: str = ""
    video: str = ""


@router.post("/")
def submit_project(data: ProjectSubmit, db: sqlite3.Connection = Depends(get_db)):
    """Submit a new project."""
    payload = decode_token(data.token)
    if not payload:
        raise HTTPException(401, "Please log in to submit a project.")

    user_id = payload.get("uid")
    cur = db.execute("""
        INSERT INTO students (
            user_id, name, email, phone, college, degree, year,
            linkedin, availability, jobrole, city, tatti_course, stipend,
            status, domain, ptitle, pdesc, impact, skills,
            github, demo, video, is_new
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        user_id, data.name, data.email, data.phone, data.college,
        data.degree, data.year, data.linkedin, data.availability,
        data.jobrole, data.city, data.tatti_course, data.stipend,
        data.domain, data.ptitle, data.pdesc, data.impact,
        json.dumps(data.skills), data.github, data.demo, data.video
    ))
    db.commit()
    return {"id": cur.lastrowid, "message": "Project published successfully!"}


@router.post("/me/resume")
async def upload_resume(file: UploadFile = File(...), token: str = Form(...),
                        db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    
    user_id = payload.get("uid")
    
    # Try to find an existing student profile for this user
    student = db.execute("SELECT id FROM students WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 1", (user_id,)).fetchone()
    
    if not student:
        # Create a stub profile if none exists
        db.execute("""
            INSERT INTO students (user_id, name, email, ptitle, pdesc, demo)
            VALUES (?, ?, ?, 'Profile', 'Personal profile', '')
        """, (user_id, payload.get("name"), payload.get("sub")))
        db.commit()
        student = db.execute("SELECT id FROM students WHERE user_id = ?", (user_id,)).fetchone()

    actual_student_id = student["id"]
    ext = os.path.splitext(file.filename)[1]
    filename = f"resume_{actual_student_id}{ext}"
    path = UPLOAD_DIR / filename

    with open(str(path), "wb") as f:
        shutil.copyfileobj(file.file, f)

    db.execute("UPDATE students SET resume_path = ? WHERE user_id = ?", (filename, user_id))
    db.commit()
    return {"message": "Resume uploaded", "filename": filename}


@router.delete("/{student_id}")
def delete_project(student_id: int, token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")

    student = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(404, "Student not found")

    # Only owner or admin can delete
    if student["email"] != payload.get("sub") and payload.get("role") != "admin":
        raise HTTPException(403, "You can only delete your own projects.")

    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.execute("DELETE FROM shortlist WHERE student_id = ?", (student_id,))
    db.commit()
    return {"message": "Project deleted."}


@router.get("/my/projects")
def get_my_projects(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    email = payload.get("sub")
    rows = db.execute("SELECT * FROM students WHERE email = ? ORDER BY submitted_at DESC", (email,)).fetchall()
    projects = []
    for r in rows:
        d = dict(r)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        d["tatti_certified"] = bool(d["tatti_certified"])
        d["is_new"] = bool(d["is_new"])
        projects.append(d)
    return {"projects": projects}


class StudentUpdate(BaseModel):
    token: str
    phone: Optional[str] = None
    city: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: Optional[list[str]] = None
    experience: Optional[str] = None

@router.post("/update-profile")
def update_student_profile(data: StudentUpdate, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(data.token)
    if not payload:
        raise HTTPException(401, "Unauthorized")
    
    email = payload.get("sub")
    
    # Update all student records associated with this email (if they have multiple projects)
    # or just the latest/master profile. Assuming we update all for consistency.
    db.execute("""
        UPDATE students SET 
            phone = COALESCE(?, phone),
            city = COALESCE(?, city),
            linkedin = COALESCE(?, linkedin),
            github = COALESCE(?, github),
            portfolio_url = COALESCE(?, portfolio_url),
            skills = COALESCE(?, skills),
            experience = COALESCE(?, experience)
        WHERE email = ?
    """, (
        data.phone, data.city, data.linkedin, data.github, 
        data.portfolio_url, 
        json.dumps(data.skills) if data.skills is not None else None,
        data.experience,
        email
    ))
    db.commit()
    return {"message": "Profile updated successfully"}


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
            if payload.get("sub") == "admin@tatti.in" or payload.get("role") == "admin":
                is_authorized = True
            elif payload.get("role") == "hr":
                # Check actual database for 'approved' status
                hr = db.execute("SELECT approved FROM hr_users WHERE email=?", (payload["sub"],)).fetchone()
                if hr and hr[0]: is_authorized = True

    rows = db.execute("""
        SELECT id, name, email, phone, college, degree, year, linkedin,
               availability, jobrole, city, tatti_course, stipend,
               status, domain, ptitle, pdesc, impact, skills,
               github, demo, video, resume_path, has_resume, tatti_certified, is_new, submitted_at
        FROM students
        WHERE ptitle IS NOT NULL AND ptitle != ''
          AND pdesc IS NOT NULL AND pdesc != ''
          AND demo IS NOT NULL AND demo != ''
        ORDER BY submitted_at DESC
    """).fetchall()

    students = []
    for r in rows:
        d = dict(r)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        d["tatti_certified"] = bool(d["tatti_certified"])
        d["is_new"] = bool(d["is_new"])
        # has_resume: true if dedicated column set OR resume uploaded OR drive link present
        d["has_resume"] = bool(d.get("has_resume") or d.get("resume_path") or d.get("github"))
        
        # Redact contact details for non-authorized users
        if not is_authorized:
            for field in ["email", "phone", "linkedin", "github", "demo", "video", "resume_path"]:
                d[field] = None
            # Keep has_resume as boolean signal (don't expose the link)
            # has_resume stays True so filters still work meaningfully

        students.append(d)
    return {"students": students, "total": len(students)}


@router.get("/{student_id}")
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Student not found.")
    d = dict(row)
    d["skills"] = json.loads(d["skills"]) if d["skills"] else []
    d["tatti_certified"] = bool(d["tatti_certified"])
    d["is_new"] = bool(d["is_new"])
    d["has_resume"] = bool(d["resume_path"])
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


@router.post("/{student_id}/resume")
async def upload_resume(student_id: int, file: UploadFile = File(...), token: str = Form(...),
                        db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Unauthorized")

    student = db.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        raise HTTPException(404, "Student not found")

    ext = os.path.splitext(file.filename)[1]
    filename = f"resume_{student_id}{ext}"
    path = UPLOAD_DIR / filename

    with open(str(path), "wb") as f:
        shutil.copyfileobj(file.file, f)

    db.execute("UPDATE students SET resume_path = ? WHERE id = ?", (filename, student_id))
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

"""
Auth routes: student register/login, HR register/login, token verification.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, validator
import sqlite3
import json
from app.database import get_db
from app.utils import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request schemas ──
class StudentRegister(BaseModel):
    name: str
    email: str
    password: str

class StudentLogin(BaseModel):
    email: str
    password: str

class HRRegister(BaseModel):
    name: str
    email: str
    password: str
    company: str
    designation: str
    intent: str = ""
    requirements: str = ""

    @validator('designation')
    def validate_designation(cls, v):
        allowed = ["HR Manager", "Talent Acquisition", "Recruiter", "Hiring Manager", "Other"]
        if v not in allowed:
            # Fallback for minor typos or old entries
            return v if v else "Recruiter"
        return v

class HRLogin(BaseModel):
    email: str
    password: str


# ── Student Auth ──
@router.post("/register")
def register_student(data: StudentRegister, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM users WHERE email = ?", (data.email,)).fetchone()
    if existing:
        raise HTTPException(400, "An account with this email already exists.")
    hashed = hash_password(data.password)
    cur = db.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, 'student')",
        (data.name, data.email, hashed)
    )
    db.commit()
    token = create_token({"sub": data.email, "role": "student", "name": data.name, "uid": cur.lastrowid})
    return {"token": token, "name": data.name, "email": data.email, "role": "student"}


@router.post("/login")
def login_student(data: StudentLogin, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM users WHERE email = ?", (data.email,)).fetchone()
    if not user:
        raise HTTPException(401, "No account found. Please register first.")
    if not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Incorrect password.")
    token = create_token({"sub": user["email"], "role": user["role"], "name": user["name"], "uid": user["id"]})
    return {"token": token, "name": user["name"], "email": user["email"], "role": user["role"]}


# ── HR Auth ──
@router.post("/hr/register")
def register_hr(data: HRRegister, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM hr_users WHERE email = ?", (data.email,)).fetchone()
    if existing:
        raise HTTPException(400, "An HR account with this email already exists.")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    
    db.execute("""
        INSERT INTO hr_users (name, email, password, company, designation, intent, requirements, approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
    """, (data.name, data.email, hash_password(data.password), data.company, data.designation, data.intent, data.requirements))
    db.commit()

    token = create_token({
        "sub": data.email, "role": "hr", "name": data.name,
        "company": data.company, "approved": 0
    })
    
    return {
        "token": token, "email": data.email, "name": data.name, "role": "hr",
        "company": data.company, "approved": False
    }


@router.post("/hr/login")
def login_hr(data: HRLogin, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute("SELECT * FROM hr_users WHERE email = ?", (data.email,)).fetchone()
    if not user:
        raise HTTPException(401, "No HR account found. Please register first.")
    if not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Incorrect password.")
    token = create_token({
        "sub": user["email"], "role": "hr", "name": user["name"],
        "company": user["company"], "uid": user["id"], "approved": bool(user["approved"])
    })
    return {
        "token": token, "email": user["email"], "name": user["name"], "role": "hr",
        "company": user["company"], "approved": bool(user["approved"])
    }


# ── Token verification ──
@router.get("/me")
def get_me(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token.")
    
    approved = False
    if payload.get("role") == "hr":
        res = db.execute("SELECT approved FROM hr_users WHERE email=?", (payload.get("sub"),)).fetchone()
        if res: approved = bool(res[0])

    return {
        "email": payload.get("sub"), "name": payload.get("name"), 
        "role": payload.get("role"), "company": payload.get("company", ""),
        "approved": approved
    }

"""
Admin routes: approve HR accounts, view all HR registrations, stats.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
from app.database import get_db
from app.utils import decode_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(token: str):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid token.")
    # Admin can be: role=admin, or the default admin email
    if payload.get("role") not in ("admin", "hr") or payload.get("sub") != "admin@tatti.in":
        # Also allow any HR with admin role
        if payload.get("role") != "admin":
            raise HTTPException(403, "Admin access required.")
    return payload


@router.get("/hr-accounts")
def list_hr_accounts(token: str, db: sqlite3.Connection = Depends(get_db)):
    _require_admin(token)
    rows = db.execute("""
        SELECT id, name, email, company, designation, intent, requirements, approved, created_at
        FROM hr_users WHERE email != 'admin@tatti.in'
        ORDER BY created_at DESC
    """).fetchall()
    accounts = [dict(r) for r in rows]
    for a in accounts:
        a["approved"] = bool(a["approved"])
    return {"accounts": accounts}


class ApproveHR(BaseModel):
    token: str
    hr_email: str


@router.post("/approve-hr")
def approve_hr(data: ApproveHR, db: sqlite3.Connection = Depends(get_db)):
    _require_admin(data.token)
    hr = db.execute("SELECT id FROM hr_users WHERE email = ?", (data.hr_email,)).fetchone()
    if not hr:
        raise HTTPException(404, "HR account not found.")
    db.execute("UPDATE hr_users SET approved = 1 WHERE email = ?", (data.hr_email,))
    db.commit()
    return {"message": f"HR account {data.hr_email} approved."}


@router.get("/activity")
def get_all_activity(token: str, db: sqlite3.Connection = Depends(get_db)):
    _require_admin(token)
    rows = db.execute("""
        SELECT sl.id, sl.hr_email, sl.stage, sl.note, sl.created_at,
               s.name as student_name, s.college as student_college, s.ptitle as student_project,
               hr.name as hr_name, hr.company as hr_company
        FROM shortlist sl
        JOIN students s ON sl.student_id = s.id
        JOIN hr_users hr ON sl.hr_email = hr.email
        ORDER BY sl.created_at DESC
    """).fetchall()
    return {"activity": [dict(r) for r in rows]}


@router.get("/stats")
def admin_stats(token: str, db: sqlite3.Connection = Depends(get_db)):
    _require_admin(token)
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_hr = db.execute("SELECT COUNT(*) FROM hr_users WHERE email != 'admin@tatti.in'").fetchone()[0]
    approved_hr = db.execute("SELECT COUNT(*) FROM hr_users WHERE approved = 1 AND email != 'admin@tatti.in'").fetchone()[0]
    pending_hr = total_hr - approved_hr
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_selections = db.execute("SELECT COUNT(*) FROM shortlist").fetchone()[0] # New stat
    return {
        "total_students": total_students,
        "total_hr": total_hr,
        "approved_hr": approved_hr,
        "pending_hr": pending_hr,
        "total_users": total_users,
        "total_selections": total_selections
    }

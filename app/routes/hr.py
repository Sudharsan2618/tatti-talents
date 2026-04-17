"""
HR dashboard routes: shortlist, pipeline tracking, notes, export.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sqlite3
import json
from app.database import get_db
from app.utils import decode_token

router = APIRouter(prefix="/api/hr", tags=["hr"])


def _require_hr(token: str):
    payload = decode_token(token)
    if not payload or payload.get("role") not in ("hr", "admin"):
        raise HTTPException(401, "HR login required.")
    return payload


class ShortlistAction(BaseModel):
    token: str
    student_id: int

class UpdateStage(BaseModel):
    token: str
    student_id: int
    stage: str

class UpdateNote(BaseModel):
    token: str
    student_id: int
    note: str


@router.get("/shortlist")
def get_shortlist(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(token)
    hr_email = payload["sub"]
    
    rows = db.execute("""
        SELECT sl.student_id, sl.stage, sl.note, sl.created_at,
               s.name, s.email, s.phone, s.college, s.degree, s.year,
               s.domain, s.ptitle, s.pdesc, s.impact, s.skills,
               s.github, s.demo, s.video, s.resume_path, s.status, s.tatti_certified
        FROM shortlist sl
        JOIN students s ON sl.student_id = s.id
        WHERE sl.hr_email = ?
        ORDER BY sl.created_at DESC
    """, (hr_email,)).fetchall()

    items = []
    for r in rows:
        d = dict(r)
        d["skills"] = json.loads(d["skills"]) if d["skills"] else []
        d["tatti_certified"] = bool(d["tatti_certified"])
        items.append(d)
    return {"shortlist": items}


@router.post("/shortlist/add")
def add_to_shortlist(data: ShortlistAction, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(data.token)
    hr_email = payload["sub"]

    existing = db.execute(
        "SELECT id FROM shortlist WHERE hr_email = ? AND student_id = ?",
        (hr_email, data.student_id)
    ).fetchone()
    if existing:
        raise HTTPException(400, "Already in shortlist.")

    db.execute(
        "INSERT INTO shortlist (hr_email, student_id, stage) VALUES (?, ?, 'shortlisted')",
        (hr_email, data.student_id)
    )
    db.commit()
    return {"message": "Added to shortlist!"}


@router.post("/shortlist/remove")
def remove_from_shortlist(data: ShortlistAction, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(data.token)
    hr_email = payload["sub"]
    db.execute(
        "DELETE FROM shortlist WHERE hr_email = ? AND student_id = ?",
        (hr_email, data.student_id)
    )
    db.commit()
    return {"message": "Removed from shortlist."}


@router.post("/pipeline/stage")
def update_stage(data: UpdateStage, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(data.token)
    hr_email = payload["sub"]

    existing = db.execute(
        "SELECT id FROM shortlist WHERE hr_email = ? AND student_id = ?",
        (hr_email, data.student_id)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE shortlist SET stage = ? WHERE hr_email = ? AND student_id = ?",
            (data.stage, hr_email, data.student_id)
        )
    else:
        db.execute(
            "INSERT INTO shortlist (hr_email, student_id, stage) VALUES (?, ?, ?)",
            (hr_email, data.student_id, data.stage)
        )
    db.commit()
    return {"message": f"Stage updated to {data.stage}"}


@router.post("/pipeline/note")
def update_note(data: UpdateNote, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(data.token)
    hr_email = payload["sub"]

    existing = db.execute(
        "SELECT id FROM shortlist WHERE hr_email = ? AND student_id = ?",
        (hr_email, data.student_id)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE shortlist SET note = ? WHERE hr_email = ? AND student_id = ?",
            (data.note, hr_email, data.student_id)
        )
    else:
        db.execute(
            "INSERT INTO shortlist (hr_email, student_id, stage, note) VALUES (?, ?, 'new', ?)",
            (hr_email, data.student_id, data.note)
        )
    db.commit()
    return {"message": "Note saved."}


@router.get("/stats")
def get_stats(token: str, db: sqlite3.Connection = Depends(get_db)):
    payload = _require_hr(token)
    hr_email = payload["sub"]

    total = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    shortlisted = db.execute("SELECT COUNT(*) FROM shortlist WHERE hr_email = ?", (hr_email,)).fetchone()[0]
    contacted = db.execute(
        "SELECT COUNT(*) FROM shortlist WHERE hr_email = ? AND stage IN ('contacted','interview','offer')",
        (hr_email,)
    ).fetchone()[0]
    interviews = db.execute(
        "SELECT COUNT(*) FROM shortlist WHERE hr_email = ? AND stage = 'interview'", (hr_email,)
    ).fetchone()[0]

    # Pipeline breakdown
    pipeline = {}
    for stage in ["new", "shortlisted", "contacted", "interview", "offer", "rejected"]:
        pipeline[stage] = db.execute(
            "SELECT COUNT(*) FROM shortlist WHERE hr_email = ? AND stage = ?",
            (hr_email, stage)
        ).fetchone()[0]

    return {
        "total": total,
        "shortlisted": shortlisted,
        "contacted": contacted,
        "interviews": interviews,
        "pipeline": pipeline
    }

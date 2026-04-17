"""
SQLite database setup with connection pooling.
All tables are created on startup; seed data inserted if empty.
"""
import sqlite3
import os
import json
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "talentatlas.db"

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"

def get_db():
    """Yield a database connection for dependency injection."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables and seed data on first run."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    # ── Users table (students + admin) ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        email       TEXT NOT NULL UNIQUE,
        password    TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'student',
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── HR users table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hr_users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        email         TEXT NOT NULL UNIQUE,
        password      TEXT NOT NULL,
        company       TEXT NOT NULL,
        designation   TEXT DEFAULT '',
        intent        TEXT DEFAULT '',
        requirements  TEXT DEFAULT '',
        approved      INTEGER NOT NULL DEFAULT 0,
        created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ── Students / profiles table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER,
        name            TEXT NOT NULL,
        email           TEXT NOT NULL,
        phone           TEXT DEFAULT '',
        college         TEXT DEFAULT '',
        degree          TEXT DEFAULT '',
        year            TEXT DEFAULT '',
        linkedin        TEXT DEFAULT '',
        github          TEXT DEFAULT '',
        portfolio_url   TEXT DEFAULT '',
        experience      TEXT DEFAULT '',
        education_history TEXT DEFAULT '[]',
        availability    TEXT DEFAULT '',
        jobrole         TEXT DEFAULT '',
        city            TEXT DEFAULT '',
        tatti_course    TEXT DEFAULT '',
        stipend         TEXT DEFAULT '',
        status          TEXT DEFAULT 'available',
        domain          TEXT DEFAULT 'other',
        ptitle          TEXT NOT NULL,
        pdesc           TEXT DEFAULT '',
        impact          TEXT DEFAULT '',
        skills          TEXT DEFAULT '[]',
        demo            TEXT DEFAULT '',
        video           TEXT DEFAULT '',
        resume_path     TEXT DEFAULT '',
        tatti_certified INTEGER DEFAULT 0,
        is_new          INTEGER DEFAULT 1,
        submitted_at    TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # ── Jobs table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        hr_id           INTEGER NOT NULL,
        title           TEXT NOT NULL,
        company         TEXT NOT NULL,
        location        TEXT DEFAULT 'Remote',
        salary          TEXT DEFAULT 'Competitive',
        type            TEXT DEFAULT 'Full-time',
        description     TEXT NOT NULL,
        requirements    TEXT DEFAULT '[]',
        skills_needed   TEXT DEFAULT '[]',
        status          TEXT DEFAULT 'open',
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (hr_id) REFERENCES hr_users(id)
    )
    """)

    # ── Job Applications table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS job_applications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id          INTEGER NOT NULL,
        student_id      INTEGER NOT NULL,
        status          TEXT NOT NULL DEFAULT 'applied', -- applied, review, shortlisted, rejected, interview, offer
        cover_letter    TEXT DEFAULT '',
        resume_update   TEXT DEFAULT '',
        applied_at      TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
    """)

    # ── Bookmarks table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookmarks (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        job_id          INTEGER NOT NULL,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, job_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )
    """)

    # ── Notifications table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        title           TEXT NOT NULL,
        message         TEXT NOT NULL,
        type            TEXT DEFAULT 'info', -- info, job, hr, system
        is_read         INTEGER DEFAULT 0,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # ── Shortlist table (Original HR Favorites) ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS shortlist (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        hr_email    TEXT NOT NULL,
        student_id  INTEGER NOT NULL,
        stage       TEXT NOT NULL DEFAULT 'shortlisted',
        note        TEXT DEFAULT '',
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(hr_email, student_id),
        FOREIGN KEY (student_id) REFERENCES students(id)
    )
    """)

    # ── Challenges table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenges (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        hr_id           INTEGER NOT NULL,
        title           TEXT NOT NULL,
        description     TEXT NOT NULL,
        deadline        TEXT NOT NULL,
        skills          TEXT DEFAULT '[]',
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (hr_id) REFERENCES hr_users(id)
    )
    """)

    # ── Submissions table ──
    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id    INTEGER NOT NULL,
        student_id      INTEGER NOT NULL,
        upload_url      TEXT NOT NULL,
        status          TEXT DEFAULT 'pending',
        rating          INTEGER DEFAULT 0,
        feedback        TEXT DEFAULT '',
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (challenge_id) REFERENCES challenges(id),
        FOREIGN KEY (student_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()



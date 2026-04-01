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

    # ── Students / projects table ──
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
        github          TEXT DEFAULT '',
        demo            TEXT DEFAULT '',
        video           TEXT DEFAULT '',
        resume_path     TEXT DEFAULT '',
        tatti_certified INTEGER DEFAULT 0,
        is_new          INTEGER DEFAULT 1,
        submitted_at    TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # ── Shortlist table ──
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
    # ── Seed data if tables are empty ──
    count = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if count == 0:
        _seed_students(cur)
        conn.commit()

    count = cur.execute("SELECT COUNT(*) FROM hr_users").fetchone()[0]
    if count == 0:
        _seed_admin(cur)
        conn.commit()

    conn.close()


def _seed_admin(cur):
    """Seed distinct Admin, HR, and Student accounts."""
    from app.utils import hash_password
    
    admin_pw = hash_password("Admin@1234")
    hr_pw = hash_password("Hr@1234")
    student_pw = hash_password("Student@1234")

    # 1. Admin Account (hr_users table with approved=1 and special designation)
    cur.execute("""
        INSERT INTO hr_users (name, email, password, company, designation, intent, requirements, approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, ("Admin User", "admin@tatti.in", admin_pw, "TATTI", "System Admin", "Administration", "System Admin"))

    # 2. Separate Test HR Account (hr_users table with approved=1)
    cur.execute("""
        INSERT INTO hr_users (name, email, password, company, designation, intent, requirements, approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, ("Sundar Sir", "hr@tatti.in", hr_pw, "TechCorp", "Recruiting Manager", "Hiring Students", "React, Python"))

    # 3. Separate Test Student Account (users table)
    cur.execute("""
        INSERT OR IGNORE INTO users (name, email, password, role)
        VALUES (?, ?, ?, 'student')
    """, ("Test Student", "student@tatti.in", student_pw))


def _seed_students(cur):
    """Seed the initial batch of students from TATTI."""
    seeds = [
        {
            "name": "D. Mugil Azhagan", "email": "mugilandass0@gmail.com", "phone": "7200674050",
            "college": "Hindu College, Chennai", "degree": "B.A. Tamil - S2", "year": "3rd Year",
            "status": "available", "domain": "other",
            "ptitle": "Electrical Guardian — E-Waste Project",
            "pdesc": "An innovative project focused on saving electronic waste and promoting sustainable disposal.",
            "skills": json.dumps(["Python"]),
            "github": "", "demo": "https://tech-salvage-hero.lovable.app",
            "tatti_certified": 1, "is_new": 0
        },
        {
            "name": "Karthikeyan V", "email": "karthik23ai111@gmail.com", "phone": "8838429102",
            "college": "Hindu College, Chennai", "degree": "B.Sc Computer Science with Artificial Intelligence", "year": "3rd Year",
            "status": "available", "domain": "ai",
            "ptitle": "Ghost Phantom",
            "pdesc": "An AI-powered cybersecurity tool that analyzes system vulnerabilities using network scans and intelligently generates security insights and protection recommendations.",
            "skills": json.dumps(["Python"]),
            "github": "", "demo": "https://karthik-portfolio.framer.ai/",
            "tatti_certified": 1, "is_new": 0
        },
        {
            "name": "Esther Cindrella S", "email": "esthercindrella2636@gmail.com", "phone": "8122815591",
            "college": "Hindu College, Chennai", "degree": "B.Com Corporate Secretaryship - S2", "year": "3rd Year",
            "status": "available", "domain": "web",
            "ptitle": "ECHOEXIT",
            "pdesc": "EchoExit is a disguised web application that enables users to secretly trigger emergency assistance through covert interactions.",
            "skills": json.dumps(["Python"]),
            "github": "", "demo": "https://echoexit-pptx-20260301-205617-0000.tiiny.site",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Manoj M", "email": "m.manoj292607@gmail.com", "phone": "8939198708",
            "college": "Hindu College, Chennai", "degree": "B.Sc Computer Science with Data Science - S2", "year": "2nd Year",
            "status": "available", "domain": "mobile",
            "ptitle": "Life Link",
            "pdesc": "Smart blood search app and instant online police complaint — two-in-one emergency platform.",
            "skills": json.dumps(["Python", "Figma"]),
            "github": "", "demo": "https://crater-luxury-45738185.figma.site",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Dinakaran P", "email": "dinakaranpecerf1@gmail.com", "phone": "7397255767",
            "college": "Hindu College, Chennai", "degree": "B.Com Corporate Secretaryship - S2", "year": "2nd Year",
            "status": "open", "domain": "other",
            "ptitle": "Solar Powered EV Charging Station",
            "pdesc": "Making charge stations for EV vehicles through solar power — green energy mobility solution.",
            "skills": json.dumps(["Python"]),
            "github": "", "demo": "https://solarpoweredevchargingstation.tiiny.site",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Madhumitha S", "email": "madhu63747mitha@gmail.com", "phone": "6374782228",
            "college": "Hindu College, Chennai", "degree": "B.C.A. Computer Application - S2", "year": "2nd Year",
            "status": "available", "domain": "iot",
            "ptitle": "Child Monitoring System",
            "pdesc": "A system that protects children from online scams and harmful content by monitoring and controlling their internet activities.",
            "skills": json.dumps(["Python", "Figma"]),
            "github": "", "demo": "https://www.figma.com/make/RXJYhH8XajZq4yZ82P0CuL",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Gokul", "email": "gokugokul0510@gmail.com", "phone": "8524060489",
            "college": "Hindu College, Chennai", "degree": "B.Sc. Electronics with Artificial Intelligence", "year": "2nd Year",
            "status": "available", "domain": "iot",
            "ptitle": "BinNova: Smart Waste Management System",
            "pdesc": "An IoT-enabled smart bin network that monitors waste levels, guides citizens to nearby bins, and helps municipalities manage waste collection efficiently.",
            "skills": json.dumps(["Python", "Arduino/RPi", "Figma"]),
            "github": "", "demo": "https://jajajahsehehe.github.io/BinNova/",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Srinithi S", "email": "srinithiusha06@gmail.com", "phone": "8822779349",
            "college": "Hindu College, Chennai", "degree": "B.Sc. Electronics with Artificial Intelligence", "year": "1st Year",
            "status": "available", "domain": "ai",
            "ptitle": "Campus Guiding Robot Using Voice Module",
            "pdesc": "This robot acts as a smart assistant that enhances campus accessibility and visitor experience.",
            "skills": json.dumps(["Python", "Arduino/RPi"]),
            "github": "", "demo": "https://github.com/srinithiusha06-source/campus-guiding-robot",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "K. Anees Sheriff", "email": "cooldj2101@gmail.com", "phone": "6369924370",
            "college": "Hindu College, Chennai", "degree": "B.Com Information System & Management - S2", "year": "1st Year",
            "status": "available", "domain": "web",
            "ptitle": "EV Hub and Service",
            "pdesc": "EV batteries service and replacement app development for electric vehicle ecosystem.",
            "skills": json.dumps(["Python"]),
            "github": "", "demo": "https://codepen.io/sheaikhg-the-bold/pen/ogLKVrw",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Blessing Obed", "email": "blessingobed40@gmail.com", "phone": "9344159590",
            "college": "Hindu College, Chennai", "degree": "B.Sc Statistics - S2", "year": "2nd Year",
            "status": "available", "domain": "data",
            "ptitle": "AgriConnect-TN",
            "pdesc": "Agriculture data platform for Tamil Nadu farmers connecting supply chains and market data.",
            "skills": json.dumps(["Python", "Excel/Stats", "Figma"]),
            "github": "", "demo": "https://agriconnect-tn.my.canva.site",
            "tatti_certified": 0, "is_new": 0
        },
        {
            "name": "Nasreen Begam M", "email": "candynasreen25@gmail.com", "phone": "7871133122",
            "college": "St. Joseph College, Kovur, Chennai", "degree": "B.Sc. Computer Science", "year": "3rd Year",
            "status": "available", "domain": "web",
            "ptitle": "Grocery Store Management",
            "pdesc": "Automated grocery inventory management system to solve manual confusion in tracking.",
            "skills": json.dumps(["Python"]),
            "github": "", "demo": "https://www.linkedin.com/in/nasreen-begam-m-b231772a2",
            "tatti_certified": 0, "is_new": 0
        },
    ]

    cols = list(seeds[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_str = ", ".join(cols)

    for s in seeds:
        vals = [s[c] for c in cols]
        cur.execute(f"INSERT INTO students ({col_str}) VALUES ({placeholders})", vals)

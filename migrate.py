import sqlite3
from pathlib import Path

DB_PATH = Path("data/talentatlas.db")
conn = sqlite3.connect(str(DB_PATH))

conn.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    type       TEXT DEFAULT 'info',
    is_read    INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
""")
conn.commit()

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in DB:", [r[0] for r in tables])

notif_count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
print(f"Notifications rows: {notif_count}")

conn.close()
print("Migration complete!")

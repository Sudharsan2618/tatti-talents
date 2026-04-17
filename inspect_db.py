import sqlite3
DB_PATH = "backend/data/talentatlas.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables:", [t[0] for t in tables])
for table in tables:
    cur.execute(f"PRAGMA table_info({table[0]})")
    print(f"\nColumns for {table[0]}:")
    for col in cur.fetchall():
        print(f"  {col[1]} ({col[2]})")
conn.close()

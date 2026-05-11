import sqlite3
import bcrypt
from pathlib import Path

DB_PATH = Path("data/talentatlas.db")
conn = sqlite3.connect(str(DB_PATH))

# Check existing users and their passwords
rows = conn.execute("SELECT id, name, email, password FROM users").fetchall()
for row in rows:
    print(f"ID:{row[0]} Name:{row[1]} Email:{row[2]} PassHash:{row[3][:20]}...")

# Reset tt@gmail.com password to "password123"
new_password = "password123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(new_password.encode(), salt).decode()

conn.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, "tt@gmail.com"))
conn.commit()

# Verify the new hash works
user = conn.execute("SELECT password FROM users WHERE email='tt@gmail.com'").fetchone()
ok = bcrypt.checkpw(new_password.encode(), user[0].encode())
print(f"\nPassword reset successful: {ok}")
print(f"New login: tt@gmail.com / password123")

conn.close()

import sqlite3
import bcrypt

DB_PATH = "backend/data/talentatlas.db"
EMAIL = "admin@tatti.in"
NEW_PW = "sundar@123"

def reset():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(NEW_PW.encode('utf-8'), salt).decode('utf-8')
    
    # Check if admin exists
    cur.execute("SELECT id FROM hr_users WHERE email = ?", (EMAIL,))
    if cur.fetchone():
        cur.execute("UPDATE hr_users SET password = ?, approved = 1 WHERE email = ?", (hashed, EMAIL))
        print(f"Password for existing {EMAIL} updated successfully.")
    else:
        cur.execute("""
            INSERT INTO hr_users (name, email, password, company, designation, approved)
            VALUES (?, ?, ?, ?, ?, 1)
        """, ("Admin", EMAIL, hashed, "TATTI", "Administrator"))
        print(f"Admin account {EMAIL} created successfully.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset()

import sqlite3
import os
db_path = os.path.join('data', 'talentatlas.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
print("Notifications for user_id=2:", conn.execute("SELECT count(*) FROM notifications WHERE user_id = 2").fetchone()[0])
conn.close()

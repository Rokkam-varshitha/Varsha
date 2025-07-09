import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE appointment ADD COLUMN reason TEXT;")
    print("✅ 'reason' column added to appointment table.")
except sqlite3.OperationalError as e:
    print("ℹ️", e)

conn.commit()
conn.close()
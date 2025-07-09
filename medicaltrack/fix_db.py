import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE appointments ADD COLUMN email TEXT")
    print("✅ Added 'email' column to appointments.")
except sqlite3.OperationalError as e:
    print("ℹ️ Email column may already exist:", e)

try:
    cursor.execute("ALTER TABLE appointments ADD COLUMN phone_no TEXT")
    print("✅ Added 'phone_no' column to appointments.")
except sqlite3.OperationalError as e:
    print("ℹ️ Phone number column may already exist:", e)

conn.commit()
conn.close()

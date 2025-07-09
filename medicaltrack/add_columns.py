import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE appointments ADD COLUMN email TEXT")
    print("✅ 'email' column added to appointments table.")
except sqlite3.OperationalError:
    print("ℹ️ 'email' column might already exist.")

try:
    cursor.execute("ALTER TABLE appointments ADD COLUMN phone_no TEXT")
    print("✅ 'phone_no' column added to appointments table.")
except sqlite3.OperationalError:
    print("ℹ️ 'phone_no' column might already exist.")

conn.commit()
conn.close()
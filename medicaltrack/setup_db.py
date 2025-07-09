import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

# ✅ Updated users table with phone_no
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone_no TEXT,
        role TEXT NOT NULL
    )
''')
cursor.execute("DROP TABLE IF EXISTS appointments")

# Appointments table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_username TEXT NOT NULL,
        doctor_username TEXT NOT NULL,
        email TEXT,
        phone_no TEXT,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        reason TEXT,
        status TEXT
    )
''')

conn.commit()
# ✅ Print columns of appointments table
print("\n🔍 Columns in appointments table:")
cursor.execute("PRAGMA table_info(appointments)")
for col in cursor.fetchall():
    print(col)
conn.close()
print("✅ appointments table recreated with 'email' column.")


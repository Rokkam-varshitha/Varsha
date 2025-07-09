import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT,
    email TEXT,
    phone_no TEXT
)
""")

# Create appointments table
cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_username TEXT,
    doctor_username TEXT,
    date TEXT,
    time TEXT,
    reason TEXT,
    email TEXT,
    phone_no TEXT,
    status TEXT,
    diagnosis TEXT
);

""")

conn.commit()
conn.close()

print("✅ Database tables created successfully.")
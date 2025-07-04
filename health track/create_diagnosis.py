import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS diagnosis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_username TEXT,
    patient_username TEXT,
    diagnosis_text TEXT
)
''')

conn.commit()
conn.close()
print("✅ diagnosis table created.")

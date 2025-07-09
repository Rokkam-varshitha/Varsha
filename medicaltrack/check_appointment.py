import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM appointments")
rows = cursor.fetchall()

print("📋 Appointments in DB:")
for row in rows:
    print(row)

conn.close()
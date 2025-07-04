import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM diagnosis")
rows = cursor.fetchall()

print("📋 Diagnosis Table Data:")
if rows:
    for row in rows:
        print(row)
else:
    print("❌ No diagnosis records found.")

conn.close()

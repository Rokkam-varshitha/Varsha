# clean_db.py

import sqlite3

conn = sqlite3.connect('medtrack.db')
cursor = conn.cursor()

# Delete rows where patient_username is NULL
cursor.execute("DELETE FROM appointments WHERE patient_username IS NULL")
conn.commit()
conn.close()

print("✅ Cleaned up appointments with NULL patient_username.")

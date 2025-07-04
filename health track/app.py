from flask import Flask, render_template, request, redirect, session, send_from_directory, make_response
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from io import BytesIO
from xhtml2pdf import pisa
import smtplib
from email.message import EmailMessage
import os
app = Flask(__name__)  
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medtrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))  # 'doctor' or 'patient'
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_username = db.Column(db.String(100))
    name = db.Column(db.String(100))
    dosage = db.Column(db.String(100))
    time = db.Column(db.String(100))
class Diagnosis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_username = db.Column(db.String(100))
    patient_username = db.Column(db.String(100))
    diagnosis_text = db.Column(db.Text)
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_username = db.Column(db.String(100))
    doctor_username = db.Column(db.String(100))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Accepted', 'Rejected'
class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_username = db.Column(db.String(100))
    filename = db.Column(db.String(200))
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']     # New

        # Save user into database
        conn = sqlite3.connect('medtrack.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        ''', (username, password, role))
        conn.commit()
        conn.close()

        return redirect('/login')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        user = User.query.filter_by(username=username, password=password, role=role).first()
        if user:
            session['username'] = username
            session['role'] = role
            if role == 'doctor':
                return redirect('/doctor_dashboard')
            else:
                return redirect('/patient_dashboard')
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    # Show all patients from User table who have role = 'patient'
    patients = User.query.filter_by(role='patient').all()
    return render_template('doctor_dashboard.html', username=session['username'], patients=patients)

@app.route('/add_diagnosis/<patient_username>', methods=['GET', 'POST'])
def add_diagnosis(patient_username):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    if request.method == 'POST':
        diagnosis_text = request.form['diagnosis']
        new_diag = Diagnosis(
            doctor_username=session['username'],
            patient_username=patient_username,
            diagnosis_text=diagnosis_text
        )
        db.session.add(new_diag)
        db.session.commit()
        return redirect('/doctor_dashboard')

    return render_template('add_diagnosis.html', patient_username=patient_username)

@app.route('/view_patient_history/<patient_username>')
def view_patient_history(patient_username):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    meds = Medicine.query.filter_by(patient_username=patient_username).all()
    diagnoses = Diagnosis.query.filter_by(patient_username=patient_username).all()
    return render_template('view_patient_history.html', patient_username=patient_username, meds=meds, diagnoses=diagnoses)
@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'username' not in session or session['role'] != 'patient':
        return redirect('/login')

    if request.method == 'POST':
        patient_username = session['username']
        doctor_username = request.form['doctor_username']  # must match name in form
        date = request.form['date']
        time = request.form['time']
        reason = request.form['reason']

        conn = sqlite3.connect('medtrack.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appointments (patient_username, doctor_username, date, time, reason, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (patient_username, doctor_username, date, time, reason, 'Upcoming'))
        conn.commit()
        conn.close()

        return redirect('/patient_dashboard')

    return render_template('book_appointment.html')

@app.route('/doctor_appointments')
def doctor_appointments():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')
    appointments = Appointment.query.filter_by(doctor_username=session['username']).all()
    return render_template('doctor_appointments.html', appointments=appointments)
@app.route('/update_appointment/<int:appointment_id>/<action>')
def update_appointment(appointment_id, action):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    appointment = Appointment.query.get_or_404(appointment_id)
    if action == 'accept':
        appointment.status = 'Accepted'
    elif action == 'reject':
        appointment.status = 'Rejected'
    db.session.commit()
    return redirect('/doctor_appointments')
@app.route('/patient_dashboard')
def patient_dashboard():
    if 'role' in session and session['role'] == 'patient':
        medicines = Medicine.query.filter_by(patient_username=session['username']).all()
        return render_template('patient_dashboard.html', username=session['username'], medicines=medicines)
    return redirect('/login')
@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'username' not in session or session['role'] != 'patient':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        dosage = request.form['dosage']
        time = request.form['time']
        new_medicine = Medicine(
            patient_username=session['username'],
            name=name,
            dosage=dosage,
            time=time
        )
        db.session.add(new_medicine)
        db.session.commit()
        return redirect('/patient_dashboard')
    return render_template('add_medicine.html')

@app.route('/download_report/<patient_username>')
def download_report(patient_username):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')
    meds = Medicine.query.filter_by(patient_username=patient_username).all()
    diagnoses = Diagnosis.query.filter_by(patient_username=patient_username).all()
    rendered_html = render_template('report_template.html', patient_username=patient_username, meds=meds, diagnoses=diagnoses)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(rendered_html.encode("UTF-8")), result)

    if not pdf.err:
        response = make_response(result.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={patient_username}_report.pdf'
        return response
    else:
        return "Error generating PDF"
@app.route('/upload_report', methods=['GET', 'POST'])
def upload_report():
    if 'role' not in session or session['role'] != 'patient':
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['report']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Save in DB
            report = Report(patient_username=session['username'], filename=filename)
            db.session.add(report)
            db.session.commit()
            return redirect('/patient_dashboard')
        else:
            return "Invalid file type"
    return render_template('upload_report.html')
@app.route('/view_reports/<patient_username>')
def view_reports(patient_username):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    reports = Report.query.filter_by(patient_username=patient_username).all()
    return render_template('view_reports.html', patient_username=patient_username, reports=reports)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route("/doctor_view_appointments")
def doctor_view_appointments():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect('/login')

    doctor = session['username']
    conn = sqlite3.connect('medtrack.db')

    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE doctor_username=?", (doctor,))
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM appointments WHERE doctor_username=? AND status='Completed'", (doctor,))
    completed = cursor.fetchone()[0]
    # ✅ Fetch patient data (username, date, time, reason, id)
    cursor.execute("""
        SELECT a.id, a.patient_username, a.date, a.time, a.reason
        FROM appointments a
        WHERE a.doctor_username=? AND a.status='Upcoming'
    """, (doctor,))
    
    appointments = cursor.fetchall()
    conn.close()

    return render_template("doctor_appointments_summary.html", total=total, completed=completed, appointments=appointments)
@app.route('/solve/<int:appointment_id>', methods=['GET', 'POST'])
def solve_appointment(appointment_id):
    if 'username' not in session or session['role'] != 'doctor':
        return redirect('/login')

    conn = sqlite3.connect('medtrack.db')

    cursor = conn.cursor()

    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        cursor.execute("SELECT patient_username FROM appointments WHERE id=?", (appointment_id,))
        patient_username = cursor.fetchone()[0]
        cursor.execute("INSERT INTO diagnosis (doctor_username, patient_username, diagnosis_text) VALUES (?, ?, ?)",
                       (session['username'], patient_username, diagnosis))
        cursor.execute("UPDATE appointments SET status='Completed' WHERE id=?", (appointment_id,))
        conn.commit()
        conn.close()
        return redirect('/doctor_view_appointments')

    cursor.execute("SELECT patient_username, doctor_username, date, time, reason FROM appointments WHERE id=?", (appointment_id,))
    appointment = cursor.fetchone()
    conn.close()

    if appointment:
        return render_template('solve_appointment.html', appointment=appointment)
    else:
        return "Appointment not found"
def send_email(to, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "your_email@gmail.com"  # <-- Your Gmail
    msg['To'] = to

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login("your_email@gmail.com", "your_app_password")  # <-- Your app password
        smtp.send_message(msg)
        # 🔧 Add 'phone' column to users table if not already

def add_phone_column_once():
    conn = sqlite3.connect('medtrack.db')

    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        print("✅ 'phone' column added to users table.")
    except sqlite3.OperationalError as e:
        print("ℹ️ Phone column might already exist or failed:", e)
    conn.commit()
    conn.close()

# Call this function ONCE at app startup
add_phone_column_once()
conn = sqlite3.connect('medtrack.db')

cursor = conn.cursor()
cursor.execute("SELECT * FROM appointments")
rows = cursor.fetchall()

print("\n📋 Appointments Table Data:")
for row in rows:
    print(row)
conn.close()
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
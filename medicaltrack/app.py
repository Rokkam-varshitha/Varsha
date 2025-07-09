from flask import Flask, render_template, request, redirect, session, send_from_directory, make_response, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from io import BytesIO
from xhtml2pdf import pisa
import smtplib
from email.message import EmailMessage
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'medtrack.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)
#migrate = Migrate(app, db)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
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
    reason = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Accepted', 'Rejected', 'Upcoming', 'Completed'

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_username = db.Column(db.String(100))
    filename = db.Column(db.String(200))

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not all([name, email, password, role]):
            flash('Please fill all fields', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists!', 'danger')
            return redirect(url_for('signup'))

        new_user = User(username=name, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['role'] = user.role
            flash('Login successful!', 'success')
            if user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')
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
    # Only allow patients to access this route
    if 'role' not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for('login'))
    if session['role'] != 'patient':
        flash("Only patients can access the book appointment page.", "danger")
        return redirect(url_for('login'))

    # Get all doctors from the database (automatically includes all registered doctors)
    doctors = User.query.filter_by(role='doctor').all()
    doctor_names = [doctor.username for doctor in doctors]

    if request.method == 'POST':
        patient_username = session['username']
        doctor_username = request.form['doctor_username']
        date = request.form['date']
        time = request.form['time']
        reason = request.form['reason']

        # Prevent duplicate appointments for the same doctor, date, and time
        existing = Appointment.query.filter_by(
            doctor_username=doctor_username,
            date=date,
            time=time
        ).first()
        if existing:
            flash("This time slot is already booked with the selected doctor. Please choose another time.", "danger")
            return redirect(url_for('book_appointment'))

        new_appointment = Appointment(
            patient_username=patient_username,
            doctor_username=doctor_username,
            date=date,
            time=time,
            reason=reason,
            status='Upcoming'
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash(f"Appointment booked successfully with {doctor_username} on {date} at {time}!", "success")
        return redirect(url_for('patient_dashboard'))

    return render_template('book_appointment.html', doctor_names=doctor_names, now=datetime.now)

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

@app.route('/add_medicine/<patient_username>', methods=['GET', 'POST'])
def add_medicine(patient_username):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        dosage = request.form['dosage']
        time = request.form['time']
        new_medicine = Medicine(
            patient_username=patient_username,
            name=name,
            dosage=dosage,
            time=time
        )
        db.session.add(new_medicine)
        db.session.commit()
        flash('Medicine added successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))
    return render_template('add_medicine.html', patient_username=patient_username)

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

            report = Report(patient_username=session['username'], filename=filename)
            db.session.add(report)
            db.session.commit()
            return redirect('/patient_dashboard')
        else:
            return "Invalid file type"
    return render_template('upload_report.html')

@app.route('/patient_dashboard')
def patient_dashboard():
    if 'role' in session and session['role'] == 'patient':
        medicines = Medicine.query.filter_by(patient_username=session['username']).all()
        appointments = Appointment.query.filter_by(patient_username=session['username']).all()
        return render_template('patient_dashboard.html', username=session['username'], medicines=medicines, appointments=appointments)
    return redirect('/login')

@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect('/login')
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_username != session['username']:
        flash("You can only cancel your own appointments.", "danger")
        return redirect(url_for('patient_dashboard'))
    db.session.delete(appointment)
    db.session.commit()
    flash("Appointment cancelled successfully.", "success")
    return redirect(url_for('patient_dashboard'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/view_reports/<patient_username>')
def view_reports(patient_username):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect('/login')

    reports = Report.query.filter_by(patient_username=patient_username).all()
    latest_appointment = Appointment.query.filter_by(
        patient_username=patient_username,
        doctor_username=session['username']
    ).order_by(Appointment.id.desc()).first()
    latest_appointment_id = latest_appointment.id if latest_appointment else None

    return render_template(
        'view_reports.html',
        patient_username=patient_username,
        reports=reports,
        latest_appointment_id=latest_appointment_id
    )

@app.route('/view_diagnosis')
def view_diagnosis():
    if 'role' not in session or session['role'] != 'patient':
        return redirect('/login')
    diagnoses = Diagnosis.query.filter_by(patient_username=session['username']).all()
    return render_template('view_diagnosis.html', diagnoses=diagnoses)

@app.route("/doctor_view_appointments")
def doctor_view_appointments():
    if 'username' not in session or session['role'] != 'doctor':
        return redirect('/login')

    doctor = session['username']
    total = Appointment.query.filter_by(doctor_username=doctor).count()
    completed = Appointment.query.filter_by(doctor_username=doctor, status='Completed').count()
    appointments = Appointment.query.filter_by(doctor_username=doctor, status='Upcoming').all()

    # appointments is a list of Appointment objects, not tuples!
    return render_template("doctor_appointments_summary.html", total=total, completed=completed, appointments=appointments)

@app.route("/solve_appointment/<int:appointment_id>", methods=['GET', 'POST'])
def solve_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = appointment.patient_username
    doctor = appointment.doctor_username
    date = appointment.date
    time_ = appointment.time
    reason = appointment.reason

    user = User.query.filter_by(username=patient).first()
    patient_email = user.email if user else None

    if request.method == 'POST':
        solution = request.form['diagnosis']
        appointment.status = 'Completed'
        db.session.commit()

        if patient_email:
            subject = f"Diagnosis from Dr. {doctor}"
            body = f"""Dear {patient},

Your appointment on {date} at {time_} regarding "{reason}" has been reviewed.

Diagnosis:
{solution}

Regards,
MedTrack Team
"""
            send_email(patient_email, subject, body)

        return redirect("/doctor_view_appointments")

    # For GET requests, render the template and pass the appointment object
    return render_template(
        "solve_appointment.html",
        appointment=appointment,
        patient=patient,
        doctor=doctor,
        date=date,
        time=time_,
        reason=reason
    )
@app.route('/profile')
def profile():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            return render_template('profile.html', user=user)
        else:
            flash("User not found!", "danger")
            return redirect(url_for('login'))
    else:
        flash("Please log in to access your profile.", "warning")
        return redirect(url_for('login'))

@app.route('/find_doctor', methods=['GET', 'POST'])
def find_doctor():
    doctor_data = {
        'Cardiologist': {
            'name': 'Dr. A. Sharma',
            'specialty': 'Cardiologist',
            'experience': 10,
            'contact': '9876543210',
            'email': 'asharma@medtrack.com'
        },
        'Neurologist': {
            'name': 'Dr. R. Mehta',
            'specialty': 'Neurologist',
            'experience': 8,
            'contact': '8765432109',
            'email': 'rmehta@medtrack.com'
        },
        'Dermatologist': {
            'name': 'Dr. K. Patel',
            'specialty': 'Dermatologist',
            'experience': 7,
            'contact': '9876234560',
            'email': 'kpatel@medtrack.com'
        },
        'Pediatrician': {
            'name': 'Dr. S. Verma',
            'specialty': 'Pediatrician',
            'experience': 12,
            'contact': '9811122334',
            'email': 'sverma@medtrack.com'
        },
        'Gynecologist': {
            'name': 'Dr. R. Joshi',
            'specialty': 'Gynecologist',
            'experience': 15,
            'contact': '9822233445',
            'email': 'rjoshi@medtrack.com'
        },
        'Orthopedic': {
            'name': 'Dr. M. Singh',
            'specialty': 'Orthopedic',
            'experience': 9,
            'contact': '9833344556',
            'email': 'msingh@medtrack.com'
        },
        'General Physician': {
            'name': 'Dr. L. Nair',
            'specialty': 'General Physician',
            'experience': 5,
            'contact': '9844455667',
            'email': 'lnair@medtrack.com'
        },
        'ENT Specialist': {
            'name': 'Dr. V. Reddy',
            'specialty': 'ENT Specialist',
            'experience': 11,
            'contact': '9855566778',
            'email': 'vreddy@medtrack.com'
        },
        'Psychiatrist': {
            'name': 'Dr. A. Khan',
            'specialty': 'Psychiatrist',
            'experience': 6,
            'contact': '9866677889',
            'email': 'akhan@medtrack.com'
        },
        'Dentist': {
            'name': 'Dr. P. Desai',
            'specialty': 'Dentist',
            'experience': 4,
            'contact': '9877788990',
            'email': 'pdesai@medtrack.com'
        },
        'Urologist': {
            'name': 'Dr. R. Kapoor',
            'specialty': 'Urologist',
            'experience': 10,
            'contact': '9888899001',
            'email': 'rkapoor@medtrack.com'
        },
        'Oncologist': {
            'name': 'Dr. T. Iyer',
            'specialty': 'Oncologist',
            'experience': 14,
            'contact': '9899900112',
            'email': 'tiyer@medtrack.com'
        },
        'Gastroenterologist': {
            'name': 'Dr. D. Mukherjee',
            'specialty': 'Gastroenterologist',
            'experience': 13,
            'contact': '9900011223',
            'email': 'dmukherjee@medtrack.com'
        },
        'Nephrologist': {
            'name': 'Dr. S. Rao',
            'specialty': 'Nephrologist',
            'experience': 11,
            'contact': '9911122334',
            'email': 'srao@medtrack.com'
        },
        'Rheumatologist': {
            'name': 'Dr. B. Das',
            'specialty': 'Rheumatologist',
            'experience': 9,
            'contact': '9922233445',
            'email': 'bdas@medtrack.com'
        }
    }

    doctor = None
    if request.method == 'POST':
        selected = request.form.get('specialty')
        doctor = doctor_data.get(selected)

    return render_template('find_doctor.html', doctor=doctor)
def send_email(to, subject, body):
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = "meenakumarimindi@gmail.com"  # Replace with your email
    msg['To'] = to

    # Use your real email and app password below
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login("meenakumarimindi@gmail.com", "Meena@l7")
        smtp.send_message(msg)
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
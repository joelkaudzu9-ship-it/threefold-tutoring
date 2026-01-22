import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, abort, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
load_dotenv()
import requests
from datetime import datetime, timedelta
import hashlib
import uuid
from werkzeug.utils import secure_filename
from functools import wraps
import random
from sqlalchemy import text
import re

# Initialize Flask app
app = Flask(__name__)

# ============ PRODUCTION CONFIGURATION ============
# Get database URL from environment (for production) or use SQLite locally
database_url = os.environ.get('DATABASE_URL')

# Fix for Heroku/Render PostgreSQL URL format
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///threefold.db'

# Secret key from environment or fallback (change in production!)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'three-fold-ventures-secret-key-2024')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

# Production security settings
if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER'):
    app.config['DEBUG'] = False
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Disable SQLAlchemy pool for Render
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
else:
    app.config['DEBUG'] = True
    
# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ============ DATABASE MODELS ============
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    student_id = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(10), default='#4f46e5')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add relationship for lessons
    lessons = db.relationship('Lesson', backref='subject_obj', lazy=True, cascade='all, delete-orphan')


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    week_number = db.Column(db.Integer)
    day_number = db.Column(db.Integer)
    content_type = db.Column(db.String(20))
    file_path = db.Column(db.String(500))
    external_url = db.Column(db.String(500))
    duration = db.Column(db.Integer)
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    last_accessed = db.Column(db.DateTime)

    # Relationships
    user = db.relationship('User', backref='enrollments', lazy=True)
    subject = db.relationship('Subject', backref='enrollments', lazy=True)

    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'subject_id', name='unique_user_subject'),)


class Progress(db.Model):
    __tablename__ = 'progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    percentage = db.Column(db.Integer, default=0)
    last_position = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='progress_records', lazy=True)
    lesson = db.relationship('Lesson', backref='progress', lazy=True)


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='MWK')
    weeks = db.Column(db.Integer, default=1)
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Payment provider fields
    provider_reference = db.Column(db.String(100))
    provider_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    callback_data = db.Column(db.Text)

    # Verification fields
    proof_path = db.Column(db.String(500))
    verified_by = db.Column(db.Integer)
    verified_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    # Relationship
    user = db.relationship('User', backref='payments', lazy=True)


# ============ SIMPLE DATABASE INITIALIZATION ============
print("🚀 Starting THREE FOLD VENTURES application...")

# Initialize database on startup
with app.app_context():
    print("🔧 Initializing database...")
    try:
        # Create all tables
        db.create_all()
        print("✅ Tables created")
        
        # Check if we need to add initial data
        admin = User.query.filter_by(email='admin@threefoldventures.com').first()
        if not admin:
            print("🔄 Adding initial data...")
            
            # Create admin user
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                email='admin@threefoldventures.com',
                password=hashed_password,
                name='Administrator',
                phone='0888123456',
                is_admin=True
            )
            db.session.add(admin)
            
            # Create subjects if none exist
            if Subject.query.count() == 0:
                subjects_data = [
                    {'name': 'Mathematics', 'code': 'MATH', 'icon': 'fas fa-calculator', 'color': '#3B82F6',
                     'description': 'Master mathematical concepts from basics to advanced topics'},
                    {'name': 'Chemistry', 'code': 'CHEM', 'icon': 'fas fa-flask', 'color': '#10B981',
                     'description': 'Learn chemical reactions, formulas, and laboratory techniques'},
                    {'name': 'Physics', 'code': 'PHYS', 'icon': 'fas fa-atom', 'color': '#EF4444',
                     'description': 'Understand the laws of motion, energy, and the physical world'},
                    {'name': 'Agriculture', 'code': 'AGRI', 'icon': 'fas fa-tractor', 'color': '#8B5CF6',
                     'description': 'Modern farming techniques and agricultural science'},
                    {'name': 'Biology', 'code': 'BIOL', 'icon': 'fas fa-dna', 'color': '#059669',
                     'description': 'Study of living organisms and life processes'},
                    {'name': 'English', 'code': 'ENGL', 'icon': 'fas fa-book', 'color': '#DC2626',
                     'description': 'Master English language, literature, and communication skills'},
                    {'name': 'Chichewa', 'code': 'CHIC', 'icon': 'fas fa-language', 'color': '#F59E0B',
                     'description': 'Malawi national language - reading, writing, and speaking'},
                    {'name': 'Geography', 'code': 'GEOG', 'icon': 'fas fa-globe-africa', 'color': '#6366F1',
                     'description': 'Study of Earth, landscapes, and human-environment interaction'},
                    {'name': 'History', 'code': 'HIST', 'icon': 'fas fa-landmark', 'color': '#8B5CF6',
                     'description': 'Explore historical events and their impact on modern society'},
                ]
                
                for subj_data in subjects_data:
                    subject = Subject(**subj_data)
                    db.session.add(subject)
            
            db.session.commit()
            print("✅ Initial data added")
        else:
            print("✅ Database already has data")
            
        print("🎉 Application ready!")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()


# ============ HELPER FUNCTIONS ============
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {
        'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v',
        'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac',
        'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'rtf',
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg',
        'zip', 'rar', '7z'
    }
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def has_access_to_subject(user_id, subject_id):
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        subject_id=subject_id,
        status='active'
    ).first()

    if not enrollment:
        return False

    payment = Payment.query.filter_by(
        user_id=user_id,
        status='completed'
    ).order_by(Payment.created_at.desc()).first()

    if not payment:
        return False

    if payment.end_date and datetime.utcnow() > payment.end_date:
        return False

    return True


def calculate_progress(user_id, subject_id):
    total_lessons = Lesson.query.filter_by(subject_id=subject_id, is_published=True).count()
    if total_lessons == 0:
        return 0

    completed_lessons = Progress.query.filter_by(
        user_id=user_id,
        completed=True
    ).join(Lesson).filter(Lesson.subject_id == subject_id).count()

    return int((completed_lessons / total_lessons) * 100)


def format_currency(value, separator=','):
    try:
        if value is None:
            return "0"
        amount = int(float(value))
        return f"{amount:{separator}}"
    except:
        return str(value)


app.jinja_env.filters['format'] = format_currency


def get_demo_video(subject_name):
    demo_videos = {
        'Mathematics': 'https://www.youtube.com/embed/Kp2bYWRQylk',
        'Chemistry': 'https://www.youtube.com/embed/ulyopnxjAZ8',
        'Physics': 'https://www.youtube.com/embed/D2FMV-2RwDk',
        'Agriculture': 'https://www.youtube.com/embed/LqvcAs5PVWQ',
        'Biology': 'https://www.youtube.com/embed/IBaXkgwi7kc',
        'English': 'https://www.youtube.com/embed/s9shPouRWCs',
        'Chichewa': 'https://www.youtube.com/embed/5Q98rYbOPag',
        'Geography': 'https://www.youtube.com/embed/WwNuvGLblJU',
        'History': 'https://www.youtube.com/embed/yqrR1dGqNp0',
    }
    return demo_videos.get(subject_name, 'https://www.youtube.com/embed/dQw4w9WgXcQ')


def extract_youtube_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'^([A-Za-z0-9_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ============ MAIN ROUTES ============
@app.route('/')
def index():
    subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('index.html', subjects=subjects)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        student_id = request.form.get('student_id', '')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error='Email already registered')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            email=email,
            password=hashed_password,
            name=name,
            phone=phone,
            student_id=student_id
        )

        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin'))

    enrollments = Enrollment.query.filter_by(user_id=current_user.id, status='active').all()
    for enrollment in enrollments:
        enrollment.progress_percentage = calculate_progress(current_user.id, enrollment.subject_id)

    payment = Payment.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).order_by(Payment.created_at.desc()).first()

    available_subjects = Subject.query.filter_by(is_active=True).all()

    return render_template('dashboard.html',
                           enrollments=enrollments,
                           payment=payment,
                           available_subjects=available_subjects)


@app.route('/subjects')
def subjects():
    all_subjects = Subject.query.filter_by(is_active=True).all()
    return render_template('subjects.html', subjects=all_subjects)


@app.route('/subject/<int:subject_id>')
@login_required
def subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    can_access = has_access_to_subject(current_user.id, subject_id)
    demo_video = get_demo_video(subject.name)

    lessons = Lesson.query.filter_by(
        subject_id=subject_id,
        is_published=True
    ).order_by(Lesson.week_number, Lesson.day_number, Lesson.order).all()

    lessons_by_week = {}
    for lesson in lessons:
        week_key = f"Week {lesson.week_number}"
        if week_key not in lessons_by_week:
            lessons_by_week[week_key] = []
        lessons_by_week[week_key].append(lesson)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        subject_id=subject_id
    ).first()

    return render_template('subject.html',
                           subject=subject,
                           can_access=can_access,
                           lessons_by_week=lessons_by_week,
                           enrollment=enrollment,
                           demo_video=demo_video)


@app.route('/enroll/<int:subject_id>')
@login_required
def enroll(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    existing = Enrollment.query.filter_by(
        user_id=current_user.id,
        subject_id=subject_id
    ).first()

    if not existing:
        enrollment = Enrollment(
            user_id=current_user.id,
            subject_id=subject_id
        )
        db.session.add(enrollment)
        db.session.commit()

    return redirect(url_for('subject_detail', subject_id=subject_id))


@app.route('/lesson/<int:lesson_id>')
@login_required
def view_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    subject_id = lesson.subject_id

    if not has_access_to_subject(current_user.id, subject_id):
        abort(403)

    progress = Progress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson_id
    ).first()

    if not progress:
        progress = Progress(
            user_id=current_user.id,
            lesson_id=lesson_id
        )
        db.session.add(progress)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        subject_id=subject_id
    ).first()

    if enrollment:
        enrollment.last_accessed = datetime.utcnow()

    db.session.commit()

    content = None
    if lesson.content_type == 'youtube' and lesson.external_url:
        content = {'type': 'youtube', 'url': lesson.external_url}
    elif lesson.content_type in ['video', 'audio'] and lesson.file_path:
        content = {'type': lesson.content_type, 'url': lesson.file_path}
    elif lesson.content_type == 'pdf' and lesson.file_path:
        content = {'type': 'pdf', 'url': lesson.file_path}
    elif lesson.content_type == 'document' and lesson.file_path:
        content = {'type': 'document', 'url': lesson.file_path, 'filename': lesson.file_path.split('/')[-1]}
    else:
        content = {'type': 'youtube', 'url': get_demo_video(lesson.subject_obj.name)}

    return render_template('lesson.html',
                         lesson=lesson,
                         content=content,
                         progress=progress)


@app.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    if not current_user.is_admin:
        lesson = Lesson.query.filter_by(file_path=f"/static/uploads/{filename}").first()
        if lesson:
            if not has_access_to_subject(current_user.id, lesson.subject_id):
                abort(403)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/mark_complete/<int:lesson_id>')
@login_required
def mark_complete(lesson_id):
    progress = Progress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson_id
    ).first()

    if progress:
        progress.completed = True
        progress.percentage = 100
        db.session.commit()

    return redirect(request.referrer or url_for('dashboard'))


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/profile')
@login_required
def profile():
    payments = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    return render_template('profile.html', payments=payments)


# ============ PAYMENT ROUTES ============
@app.route('/payment-options')
@login_required
def payment_options():
    return render_template('payment_options.html')


@app.route('/make-payment/<method>/<weeks>')
@login_required
def make_payment(method, weeks):
    try:
        weeks = int(weeks)
    except:
        weeks = 1

    if weeks == 1:
        amount = 10000
    elif weeks == 4:
        amount = 35000
    elif weeks == 8:
        amount = 65000
    elif weeks == 12:
        amount = 95000
    else:
        amount = weeks * 10000

    method_names = {
        'tnm': 'TNM Mpamba',
        'airtel': 'Airtel Money',
        'nbs': 'NBS Bank',
        'paychangu': 'PayChangu',
        'nbm': 'National Bank',
        'bursary': 'Three Fold Bursary'
    }

    ref_number = f"TFV{random.randint(100000, 999999)}"

    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        currency='MWK',
        weeks=weeks,
        payment_method=method_names.get(method, method),
        transaction_id=ref_number,
        status='pending' if method != 'bursary' else 'pending_approval',
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(weeks=weeks),
        provider_reference=None,
        provider_name=None,
        phone_number=None,
        callback_data=None,
        verified_at=None
    )

    db.session.add(payment)
    db.session.commit()
    session['pending_payment_id'] = payment.id
    session.modified = True

    if method == 'bursary':
        return redirect(url_for('bursary_application'))

    return redirect(url_for('payment_instructions', method=method))


@app.route('/payment-instructions/<method>')
@login_required
def payment_instructions(method):
    payment_id = session.get('pending_payment_id')
    if not payment_id:
        flash('Please start a payment first', 'error')
        return redirect(url_for('payment_options'))

    payment = Payment.query.get(payment_id)
    if not payment:
        session.pop('pending_payment_id', None)
        flash('Payment not found. Please try again.', 'error')
        return redirect(url_for('payment_options'))

    if payment.user_id != current_user.id:
        session.pop('pending_payment_id', None)
        abort(403)

    instructions = {
        'tnm': {
            'title': 'TNM Mpamba Payment',
            'steps': [
                'Dial *444# on your TNM line',
                'Select "Pay Bill"',
                'Enter Business Number: 123456',
                'Enter Account Number: ' + str(payment.transaction_id),
                'Enter Amount: ' + str(payment.amount) + ' MWK',
                'Enter your PIN to complete'
            ],
            'contact': 'Customer Care: 0888 123 456',
            'note': 'Payment is processed within 5 minutes'
        },
        'airtel': {
            'title': 'Airtel Money Payment',
            'steps': [
                'Dial *555# on your Airtel line',
                'Select "Make Payment"',
                'Select "Pay Merchant"',
                'Enter Merchant Code: 888888',
                'Enter Amount: ' + str(payment.amount) + ' MWK',
                'Enter Reference: ' + str(payment.transaction_id),
                'Enter your PIN to complete'
            ],
            'contact': 'Customer Care: 0999 123 456',
            'note': 'Payment confirmation takes 2-3 minutes'
        },
        'nbs': {
            'title': 'NBS Bank Payment',
            'steps': [
                'Login to NBS Internet Banking',
                'Select "Bill Payments"',
                'Select "Education Payments"',
                'Select "THREE FOLD VENTURES"',
                'Enter Amount: ' + str(payment.amount) + ' MWK',
                'Enter Reference: ' + str(payment.transaction_id),
                'Confirm transaction'
            ],
            'contact': 'Bank Contact: 0188 12345',
            'note': 'Bank payments may take 1-2 hours to process'
        },
        'paychangu': {
            'title': 'PayChangu Payment',
            'steps': [
                'Open PayChangu App',
                'Tap "Pay Bill"',
                'Search for "THREE FOLD VENTURES"',
                'Enter Amount: ' + str(payment.amount) + ' MWK',
                'Enter Reference: ' + str(payment.transaction_id),
                'Tap "Pay Now" and confirm'
            ],
            'contact': 'Support: support@paychangu.com',
            'note': 'Instant payment processing'
        },
        'nbm': {
            'title': 'National Bank Payment',
            'steps': [
                'Use National Bank Mobile App',
                'Go to "Payments" section',
                'Select "School Fees"',
                'Search "THREE FOLD VENTURES"',
                'Enter Amount: ' + str(payment.amount) + ' MWK',
                'Enter Reference Number: ' + str(payment.transaction_id),
                'Authenticate with OTP/PIN'
            ],
            'contact': 'Bank Contact: 0182 12345',
            'note': 'Processing time: 30 minutes to 2 hours'
        }
    }

    method_data = instructions.get(method, {
        'title': 'Payment Instructions',
        'steps': ['Please follow your chosen payment method'],
        'contact': 'Contact support for assistance',
        'note': ''
    })

    return render_template('payment_instructions.html',
                           payment=payment,
                           method=method,
                           instructions=method_data)


@app.route('/confirm-payment', methods=['POST'])
@login_required
def confirm_payment():
    payment_id = session.get('pending_payment_id')
    if not payment_id:
        return redirect(url_for('payment_options'))

    payment = Payment.query.get(payment_id)
    payment.status = 'completed'
    db.session.commit()
    session.pop('pending_payment_id', None)

    return redirect(url_for('payment_success'))


@app.route('/bursary-application')
@login_required
def bursary_application():
    return render_template('bursary_application.html')


@app.route('/submit-bursary', methods=['POST'])
@login_required
def submit_bursary():
    bursary_type = request.form.get('bursary_type')
    student_id = request.form.get('student_id')
    guardian_name = request.form.get('guardian_name')
    guardian_phone = request.form.get('guardian_phone')
    reason = request.form.get('reason')

    payment = Payment(
        user_id=current_user.id,
        amount=0,
        currency='MWK',
        weeks=4,
        payment_method='Three Fold Bursary - ' + bursary_type,
        transaction_id=f"BURSARY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        status='pending_approval',
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(weeks=4)
    )

    db.session.add(payment)
    db.session.commit()

    return redirect(url_for('bursary_submitted'))


@app.route('/bursary-submitted')
@login_required
def bursary_submitted():
    return render_template('bursary_submitted.html')


@app.route('/payment-success')
@login_required
def payment_success():
    payment = Payment.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).order_by(Payment.created_at.desc()).first()

    return render_template('payment_success.html', payment=payment)


@app.route('/check-init')
def check_init():
    info = {
        'Database URI': app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET'),
        'DATABASE_URL env': os.environ.get('DATABASE_URL', 'NOT SET'),
        'On Render?': 'RENDER' in os.environ,
    }
    
    html = "<h1>Database Initialization Check</h1>"
    for key, value in info.items():
        html += f"<p><strong>{key}:</strong> {value}</p>"
    
    try:
        with app.app_context():
            user_count = User.query.count()
            subject_count = Subject.query.count()
            html += f"<p><strong>Users:</strong> {user_count}</p>"
            html += f"<p><strong>Subjects:</strong> {subject_count}</p>"
            
            if user_count == 0 and subject_count == 0:
                html += "<p style='color: red'>❌ Database appears empty!</p>"
                html += f'<p><a href="/force-init">Click here to initialize database</a></p>'
            else:
                html += "<p style='color: green'>✅ Database has data!</p>"
                
    except Exception as e:
        html += f"<p style='color: red'>❌ Error checking database: {str(e)}</p>"
    
    return html


@app.route('/force-init')
def force_initialize():
    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            
            # Create admin
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                email='admin@threefoldventures.com',
                password=hashed_password,
                name='Administrator',
                phone='0888123456',
                is_admin=True
            )
            db.session.add(admin)
            
            # Create subjects
            subjects_data = [
                {'name': 'Mathematics', 'code': 'MATH', 'icon': 'fas fa-calculator', 'color': '#3B82F6',
                 'description': 'Master mathematical concepts from basics to advanced topics'},
                {'name': 'Chemistry', 'code': 'CHEM', 'icon': 'fas fa-flask', 'color': '#10B981',
                 'description': 'Learn chemical reactions, formulas, and laboratory techniques'},
                {'name': 'Physics', 'code': 'PHYS', 'icon': 'fas fa-atom', 'color': '#EF4444',
                 'description': 'Understand the laws of motion, energy, and the physical world'},
                {'name': 'Agriculture', 'code': 'AGRI', 'icon': 'fas fa-tractor', 'color': '#8B5CF6',
                 'description': 'Modern farming techniques and agricultural science'},
                {'name': 'Biology', 'code': 'BIOL', 'icon': 'fas fa-dna', 'color': '#059669',
                 'description': 'Study of living organisms and life processes'},
                {'name': 'English', 'code': 'ENGL', 'icon': 'fas fa-book', 'color': '#DC2626',
                 'description': 'Master English language, literature, and communication skills'},
                {'name': 'Chichewa', 'code': 'CHIC', 'icon': 'fas fa-language', 'color': '#F59E0B',
                 'description': 'Malawi national language - reading, writing, and speaking'},
                {'name': 'Geography', 'code': 'GEOG', 'icon': 'fas fa-globe-africa', 'color': '#6366F1',
                 'description': 'Study of Earth, landscapes, and human-environment interaction'},
                {'name': 'History', 'code': 'HIST', 'icon': 'fas fa-landmark', 'color': '#8B5CF6',
                 'description': 'Explore historical events and their impact on modern society'},
            ]
            
            for subj_data in subjects_data:
                subject = Subject(**subj_data)
                db.session.add(subject)
            
            db.session.commit()
            
            return """
            <h1>Database Force Initialized! ✅</h1>
            <p>All tables have been recreated.</p>
            <p>✅ Admin user created: admin@threefoldventures.com / admin123</p>
            <p>✅ 9 subjects created</p>
            <p><a href="/">Go to Homepage</a> | <a href="/check-init">Check Database</a></p>
            <p style="color: orange">⚠️ Note: This route will be removed in production</p>
            """
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"


# ============ ADMIN ROUTES ============
@app.route('/admin')
@admin_required
def admin():
    total_users = User.query.count()
    total_subjects = Subject.query.count()
    total_enrollments = Enrollment.query.count()

    today = datetime.utcnow().date()
    today_registrations = User.query.filter(
        db.func.date(User.created_at) == today
    ).count()

    active_users = db.session.query(db.func.count(db.func.distinct(Enrollment.user_id))).scalar()
    pending_payments = Payment.query.filter(Payment.status.in_(['pending', 'pending_approval'])).count()
    pending_bursaries = Payment.query.filter_by(status='pending_approval').count()
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    total_completed_payments = Payment.query.filter_by(status='completed').count()

    stats = {
        'total_users': total_users,
        'total_subjects': total_subjects,
        'total_enrollments': total_enrollments,
        'total_payments': total_completed_payments,
        'total_revenue': total_revenue,
        'today_registrations': today_registrations,
        'active_users': active_users,
        'pending_payments': pending_payments,
        'pending_bursaries': pending_bursaries
    }

    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()

    return render_template('admin.html',
                           stats=stats,
                           recent_users=recent_users,
                           recent_payments=recent_payments,
                           now=datetime.utcnow())


@app.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    today = datetime.utcnow().date()
    today_count = User.query.filter(db.func.date(User.created_at) == today).count()

    return render_template('admin_users.html', users=users, today_count=today_count)


@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)
    enrollments = Enrollment.query.filter_by(user_id=user_id).count()
    payments = Payment.query.filter_by(user_id=user_id).count()
    total_paid = db.session.query(db.func.sum(Payment.amount)).filter_by(user_id=user_id,
                                                                         status='completed').scalar() or 0

    return render_template('admin_user_detail.html',
                           user=user,
                           enrollments=enrollments,
                           payments=payments,
                           total_paid=total_paid,
                           now=datetime.utcnow())


@app.route('/admin/toggle_admin/<int:user_id>')
@admin_required
def toggle_admin(user_id):
    if current_user.id == user_id:
        flash('Cannot change your own admin status', 'error')
        return redirect(url_for('admin_users'))

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()

    action = "granted" if user.is_admin else "revoked"
    flash(f'Admin privileges {action} for {user.email}', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/toggle_user_status/<int:user_id>')
@admin_required
def toggle_user_status(user_id):
    if current_user.id == user_id:
        flash('Cannot change your own status', 'error')
        return redirect(url_for('admin_users'))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    action = "activated" if user.is_active else "deactivated"
    flash(f'User {user.email} has been {action}', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/subjects')
@admin_required
def admin_subjects():
    subjects = Subject.query.all()
    return render_template('admin_subjects.html', subjects=subjects)


@app.route('/admin/subject/<int:subject_id>')
@admin_required
def admin_subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    total_lessons = Lesson.query.filter_by(subject_id=subject_id).count()
    total_enrollments = Enrollment.query.filter_by(subject_id=subject_id).count()

    return render_template('admin_subject_detail.html',
                           subject=subject,
                           total_lessons=total_lessons,
                           total_enrollments=total_enrollments)


@app.route('/admin/payments')
@admin_required
def admin_payments():
    status = request.args.get('status', 'all')
    method = request.args.get('method', 'all')

    query = Payment.query

    if status != 'all':
        query = query.filter_by(status=status)
    if method != 'all':
        query = query.filter_by(payment_method=method)

    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    pending_count = Payment.query.filter_by(status='pending_approval').count()

    today = datetime.utcnow().date()
    today_count = Payment.query.filter(
        db.func.date(Payment.created_at) == today
    ).count()

    month_start = datetime.utcnow().replace(day=1)
    month_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.created_at >= month_start
    ).scalar() or 0

    page = request.args.get('page', 1, type=int)
    per_page = 20
    payments = query.order_by(Payment.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin_payments.html',
                           payments=payments,
                           status=status,
                           method=method,
                           total_revenue=total_revenue,
                           pending_count=pending_count,
                           today_count=today_count,
                           month_revenue=month_revenue)


@app.route('/admin/update_payment_status/<int:payment_id>/<new_status>')
@admin_required
def update_payment_status(payment_id, new_status):
    payment = Payment.query.get_or_404(payment_id)
    old_status = payment.status
    payment.status = new_status

    if old_status == 'pending_approval' and new_status == 'completed':
        payment.start_date = datetime.utcnow()
        payment.end_date = datetime.utcnow() + timedelta(weeks=payment.weeks)

    db.session.commit()
    flash(f'Payment status updated from {old_status} to {new_status}', 'success')
    return redirect(url_for('admin_payments'))


@app.route('/admin/lessons')
@admin_required
def admin_lessons():
    subject_id = request.args.get('subject_id', type=int)
    query = Lesson.query

    if subject_id:
        query = query.filter_by(subject_id=subject_id)

    lessons = query.order_by(Lesson.subject_id, Lesson.week_number, Lesson.day_number).all()
    subjects = Subject.query.all()

    return render_template('admin_lessons.html',
                           lessons=lessons,
                           subjects=subjects,
                           selected_subject=subject_id)


@app.route('/admin/create_lesson', methods=['GET', 'POST'])
@admin_required
def create_lesson():
    if request.method == 'POST':
        try:
            subject_id = request.form['subject_id']
            title = request.form['title']
            description = request.form['description']
            week_number = request.form['week_number']
            day_number = request.form['day_number']
            content_type = request.form['content_type']
            duration = request.form.get('duration', 30)
            order = request.form.get('order', 1)
            is_published = 'is_published' in request.form

            lesson = Lesson(
                subject_id=subject_id,
                title=title,
                description=description,
                week_number=week_number,
                day_number=day_number,
                content_type=content_type,
                duration=duration,
                order=order,
                is_published=is_published
            )

            if content_type == 'youtube':
                youtube_url = request.form.get('youtube_url', '')
                if youtube_url:
                    video_id = extract_youtube_id(youtube_url)
                    if video_id:
                        lesson.external_url = f"https://www.youtube.com/embed/{video_id}"
                    else:
                        lesson.external_url = youtube_url

            elif 'file' in request.files and request.files['file'].filename:
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    lesson.file_path = f"/static/uploads/{unique_filename}"

                    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    if file_ext in ['mp4', 'avi', 'mov', 'mkv']:
                        lesson.content_type = 'video'
                    elif file_ext in ['mp3', 'wav', 'ogg']:
                        lesson.content_type = 'audio'
                    elif file_ext == 'pdf':
                        lesson.content_type = 'pdf'
                    elif file_ext in ['doc', 'docx', 'ppt', 'pptx']:
                        lesson.content_type = 'document'

            db.session.add(lesson)
            db.session.commit()
            flash('Lesson created successfully!', 'success')
            return redirect(url_for('admin_lessons'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating lesson: {str(e)}', 'error')
            return redirect(url_for('create_lesson'))

    subjects = Subject.query.all()
    return render_template('admin_create_lesson.html', subjects=subjects)


@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    daily_registrations = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago) \
        .group_by(db.func.date(User.created_at)) \
        .order_by('date') \
        .all()

    payment_by_method = db.session.query(
        Payment.payment_method,
        db.func.count(Payment.id).label('count'),
        db.func.sum(Payment.amount).label('total')
    ).filter(Payment.status == 'completed') \
        .group_by(Payment.payment_method) \
        .all()

    enrollment_by_subject = db.session.query(
        Subject.name,
        db.func.count(Enrollment.id).label('count')
    ).join(Enrollment.subject) \
        .group_by(Subject.name) \
        .order_by(db.func.count(Enrollment.id).desc()) \
        .all()

    return render_template('admin_analytics.html',
                           daily_registrations=daily_registrations,
                           payment_by_method=payment_by_method,
                           enrollment_by_subject=enrollment_by_subject)


@app.route('/admin/create_subject', methods=['GET', 'POST'])
@admin_required
def create_subject():
    if request.method == 'POST':
        name = request.form['name']
        code = request.form['code']
        description = request.form['description']
        icon = request.form.get('icon', 'fas fa-book')
        color = request.form.get('color', '#1e40af')

        subject = Subject(
            name=name,
            code=code,
            description=description,
            icon=icon,
            color=color
        )

        db.session.add(subject)
        db.session.commit()
        flash(f'Subject "{name}" created successfully!', 'success')
        return redirect(url_for('admin_subjects'))

    return render_template('admin_create_subject.html')


@app.route('/admin/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@admin_required
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    if request.method == 'POST':
        subject.name = request.form['name']
        subject.code = request.form['code']
        subject.description = request.form['description']
        subject.icon = request.form.get('icon', subject.icon)
        subject.color = request.form.get('color', subject.color)

        db.session.commit()
        flash(f'Subject "{subject.name}" updated successfully!', 'success')
        return redirect(url_for('admin_subjects'))

    return render_template('admin_edit_subject.html', subject=subject)


@app.route('/admin/toggle_subject/<int:subject_id>')
@admin_required
def toggle_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    subject.is_active = not subject.is_active
    db.session.commit()

    action = "activated" if subject.is_active else "deactivated"
    flash(f'Subject "{subject.name}" has been {action}', 'success')
    return redirect(url_for('admin_subjects'))


@app.route('/admin/toggle_lesson/<int:lesson_id>')
@admin_required
def toggle_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    lesson.is_published = not lesson.is_published
    db.session.commit()

    action = "published" if lesson.is_published else "unpublished"
    flash(f'Lesson "{lesson.title}" has been {action}', 'success')
    return redirect(url_for('admin_lessons'))


@app.route('/admin/edit_lesson/<int:lesson_id>', methods=['GET', 'POST'])
@admin_required
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)

    if request.method == 'POST':
        lesson.title = request.form['title']
        lesson.description = request.form['description']
        lesson.week_number = request.form['week_number']
        lesson.day_number = request.form['day_number']
        lesson.content_type = request.form['content_type']
        lesson.external_url = request.form.get('external_url', '')
        lesson.duration = request.form.get('duration', 30)
        lesson.order = request.form.get('order', 1)
        lesson.is_published = 'is_published' in request.form

        db.session.commit()
        flash(f'Lesson "{lesson.title}" updated successfully!', 'success')
        return redirect(url_for('admin_lessons'))

    subjects = Subject.query.all()
    return render_template('admin_edit_lesson.html', lesson=lesson, subjects=subjects)


# ============ ERROR HANDLERS ============
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# ============ RUN APPLICATION ============
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

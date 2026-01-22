import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, abort, flash,send_from_directory
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
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    student_id = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships - UPDATED
    enrollments = db.relationship('Enrollment', backref='user', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy=True, cascade='all, delete-orphan')  # ✅ Keep this as is
    progress_records = db.relationship('Progress', backref='user', lazy=True)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    color = db.Column(db.String(10), default='#4f46e5')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lessons = db.relationship('Lesson', backref='subject', lazy=True, cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='subject', lazy=True, cascade='all, delete-orphan')


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    week_number = db.Column(db.Integer)
    day_number = db.Column(db.Integer)
    content_type = db.Column(db.String(20))  # video, pdf, audio, text
    file_path = db.Column(db.String(500))
    external_url = db.Column(db.String(500))  # for YouTube/Vimeo embeds
    duration = db.Column(db.Integer)  # in minutes
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    progress = db.relationship('Progress', backref='lesson', lazy=True, cascade='all, delete-orphan')


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, paused, completed
    last_accessed = db.Column(db.DateTime)

    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'subject_id', name='unique_user_subject'),)


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    percentage = db.Column(db.Integer, default=0)
    last_position = db.Column(db.Integer, default=0)  # For video/audio
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='MWK')
    weeks = db.Column(db.Integer, default=1)
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, pending_verification
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Payment provider fields
    provider_reference = db.Column(db.String(100))
    provider_name = db.Column(db.String(50))
    phone_number = db.Column(db.String(20))
    callback_data = db.Column(db.Text)

    # Verification fields (SIMPLE VERSION - no foreign key for now)
    proof_path = db.Column(db.String(500))
    verified_by = db.Column(db.Integer)  # Just store user ID, NOT a foreign key
    verified_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)


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
        # Videos
        'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm', 'm4v',
        # Audio
        'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac',
        # Documents
        'pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'rtf',
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg',
        # Archives
        'zip', 'rar', '7z'
    }
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def has_access_to_subject(user_id, subject_id):
    # Check if user is enrolled and has active payment
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        subject_id=subject_id,
        status='active'
    ).first()

    if not enrollment:
        return False

    # Check if payment is active
    payment = Payment.query.filter_by(
        user_id=user_id,
        status='completed'
    ).order_by(Payment.created_at.desc()).first()

    if not payment:
        return False

    # Check if payment hasn't expired
    if payment.end_date and datetime.utcnow() > payment.end_date:
        return False

    return True


def calculate_progress(user_id, subject_id):
    # Calculate progress percentage for a subject
    total_lessons = Lesson.query.filter_by(subject_id=subject_id, is_published=True).count()
    if total_lessons == 0:
        return 0

    completed_lessons = Progress.query.filter_by(
        user_id=user_id,
        completed=True
    ).join(Lesson).filter(Lesson.subject_id == subject_id).count()

    return int((completed_lessons / total_lessons) * 100)


def format_currency(value, separator=','):
    """Format currency with custom separator"""
    try:
        if value is None:
            return "0"
        # Format with thousands separator
        amount = int(float(value))
        return f"{amount:{separator}}"
    except:
        return str(value)

# Register filter in Jinja2
app.jinja_env.filters['format'] = format_currency


def get_demo_video(subject_name):
    """Return demo YouTube video for each subject"""
    demo_videos = {
        'Mathematics': 'https://www.youtube.com/embed/Kp2bYWRQylk',  # Math basics
        'Chemistry': 'https://www.youtube.com/embed/ulyopnxjAZ8',  # Chemistry intro
        'Physics': 'https://www.youtube.com/embed/D2FMV-2RwDk',  # Physics basics
        'Agriculture': 'https://www.youtube.com/embed/LqvcAs5PVWQ',  # Farming
        'Biology': 'https://www.youtube.com/embed/IBaXkgwi7kc',  # Biology intro
        'English': 'https://www.youtube.com/embed/s9shPouRWCs',  # English grammar
        'Chichewa': 'https://www.youtube.com/embed/5Q98rYbOPag',  # Chichewa basics
        'Geography': 'https://www.youtube.com/embed/WwNuvGLblJU',  # Geography basics
        'History': 'https://www.youtube.com/embed/yqrR1dGqNp0',  # History intro
    }
    return demo_videos.get(subject_name, 'https://www.youtube.com/embed/dQw4w9WgXcQ')



# Register filter in Jinja2
app.jinja_env.filters['format'] = format_currency


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

        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error='Email already registered')

        # Create new user
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

        # Auto-login
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

            # Redirect admin to admin dashboard, others to student dashboard
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
    # If admin, redirect to admin dashboard
    if current_user.is_admin:
        return redirect(url_for('admin'))

    # Get user's enrollments with progress
    enrollments = Enrollment.query.filter_by(user_id=current_user.id, status='active').all()

    # Add progress to each enrollment
    for enrollment in enrollments:
        enrollment.progress_percentage = calculate_progress(current_user.id, enrollment.subject_id)

    # Check active payment
    payment = Payment.query.filter_by(
        user_id=current_user.id,
        status='completed'
    ).order_by(Payment.created_at.desc()).first()

    # Get available subjects
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

    # Check access
    can_access = has_access_to_subject(current_user.id, subject_id)

    # Get demo video for this subject
    demo_video = get_demo_video(subject.name)

    # Get lessons for this subject
    lessons = Lesson.query.filter_by(
        subject_id=subject_id,
        is_published=True
    ).order_by(Lesson.week_number, Lesson.day_number, Lesson.order).all()

    # Group lessons by week
    lessons_by_week = {}
    for lesson in lessons:
        week_key = f"Week {lesson.week_number}"
        if week_key not in lessons_by_week:
            lessons_by_week[week_key] = []
        lessons_by_week[week_key].append(lesson)

    # Check enrollment status
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

    # Check if already enrolled
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

    # Check access
    if not has_access_to_subject(current_user.id, subject_id):
        abort(403)

    # Record progress
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

    # Update enrollment last accessed
    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        subject_id=subject_id
    ).first()

    if enrollment:
        enrollment.last_accessed = datetime.utcnow()

    db.session.commit()

    # Determine content to display
    content = None
    if lesson.content_type == 'youtube' and lesson.external_url:
        # YouTube video
        content = {
            'type': 'youtube',
            'url': lesson.external_url
        }
    elif lesson.content_type in ['video', 'audio'] and lesson.file_path:
        # Local video/audio file
        content = {
            'type': lesson.content_type,
            'url': lesson.file_path
        }
    elif lesson.content_type == 'pdf' and lesson.file_path:
        # PDF file - open in new tab
        content = {
            'type': 'pdf',
            'url': lesson.file_path
        }
    elif lesson.content_type == 'document' and lesson.file_path:
        # Document - provide download
        content = {
            'type': 'document',
            'url': lesson.file_path,
            'filename': lesson.file_path.split('/')[-1]
        }
    else:
        # Fallback to demo video
        content = {
            'type': 'youtube',
            'url': get_demo_video(lesson.subject.name)
        }

    return render_template('lesson.html',
                         lesson=lesson,
                         content=content,
                         progress=progress)

#save uploaded files
@app.route('/uploads/<filename>')
@login_required
def serve_upload(filename):
    """Serve uploaded files (protected route)"""
    # Check if user has access
    if not current_user.is_admin:
        # For students, check if they have access to any lesson containing this file
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
    print(f"\n🔵 ========== make_payment START ==========")
    print(f"🔵 Method: {method}, Weeks: {weeks}")
    print(f"🔵 Current user: {current_user.id} ({current_user.email})")
    print(f"🔵 Session keys before: {list(session.keys())}")

    try:
        weeks = int(weeks)
    except:
        weeks = 1

    # Calculate amount based on weeks
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

    # Payment method mapping
    method_names = {
        'tnm': 'TNM Mpamba',
        'airtel': 'Airtel Money',
        'nbs': 'NBS Bank',
        'paychangu': 'PayChangu',
        'nbm': 'National Bank',
        'bursary': 'Three Fold Bursary'
    }

    # Generate reference number
    ref_number = f"TFV{random.randint(100000, 999999)}"

    # Create payment record
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

    print(f"✅ Payment created: ID={payment.id}, Amount={amount}, Ref={ref_number}")

    # Store payment ID in session for confirmation
    session['pending_payment_id'] = payment.id
    session.modified = True  # Important!
    print(f"✅ Session updated: pending_payment_id = {payment.id}")
    print(f"🔵 Session keys after: {list(session.keys())}")

    # For bursary, redirect to application
    if method == 'bursary':
        print(f"🔄 Redirecting to bursary_application")
        return redirect(url_for('bursary_application'))

    print(f"🔄 Redirecting to payment_instructions: method={method}")
    print(f"🔵 ========== make_payment END ==========\n")

    return redirect(url_for('payment_instructions', method=method))


@app.route('/api/initiate-payment/<method>', methods=['POST'])
@login_required
def initiate_payment_api(method):
    """API endpoint to initiate real payment"""
    data = request.json

    weeks = data.get('weeks', 1)
    phone = data.get('phone')

    if not phone:
        return jsonify({'error': 'Phone number required'}), 400

    # Calculate amount
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

    # Generate reference
    ref_number = f"TFV{random.randint(100000, 999999)}"

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        amount=amount,
        weeks=weeks,
        payment_method=method,
        transaction_id=ref_number,
        phone_number=phone,
        status='initiated',
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(weeks=weeks)
    )

    db.session.add(payment)
    db.session.commit()

    # Initiate payment with provider
    if method == 'tnm':
        # Initialize TNM payment
        tnm = TNMMpambaPayment(
            api_key=os.getenv('TNM_API_KEY'),
            merchant_id=os.getenv('TNM_MERCHANT_ID')
        )

        result = tnm.initiate_payment(
            amount=amount,
            phone_number=phone,
            reference=ref_number
        )

        if result and result.get('status') == 'success':
            payment.provider_reference = result.get('transaction_id')
            payment.provider_name = 'tnm'
            db.session.commit()

            return jsonify({
                'status': 'pending',
                'message': 'Payment initiated. Please check your phone.',
                'transaction_id': ref_number,
                'provider_reference': result.get('transaction_id')
            })

    elif method == 'airtel':
        # Airtel Money integration
        airtel = AirtelMoneyPayment(
            client_id=os.getenv('AIRTEL_CLIENT_ID'),
            client_secret=os.getenv('AIRTEL_CLIENT_SECRET')
        )

        result = airtel.initiate_payment(
            amount=amount,
            phone_number=phone,
            reference=ref_number
        )

        if result and result.get('status') == 'PENDING':
            payment.provider_reference = result.get('airtel_money_id')
            payment.provider_name = 'airtel'
            db.session.commit()

            return jsonify({
                'status': 'pending',
                'message': 'Payment request sent to your Airtel line',
                'transaction_id': ref_number
            })

    elif method == 'paychangu':
        # PayChangu integration
        paychangu = PayChanguPayment(api_key=os.getenv('PAYCHANGU_API_KEY'))

        result = paychangu.create_payment(
            amount=amount,
            email=current_user.email,
            phone=phone,
            reference=ref_number
        )

        if result and result.get('status') == 'success':
            payment.provider_reference = result.get('checkout_id')
            payment.provider_name = 'paychangu'
            payment.status = 'pending'
            db.session.commit()

            return jsonify({
                'status': 'redirect',
                'redirect_url': result.get('data', {}).get('checkout_url'),
                'transaction_id': ref_number
            })

    return jsonify({'error': 'Payment initiation failed'}), 500


@app.route('/payment-instructions/<method>')
@login_required
def payment_instructions(method):
    print(f"🔵 payment_instructions called: method={method}")
    # Remove or fix the session.sid line:
    # print(f"🔵 Session ID: {session.sid}")  # ❌ WRONG
    print(f"🔵 Session ID exists: {'_id' in session}")  # ✅ CORRECT
    print(f"🔵 Session keys: {list(session.keys())}")

    payment_id = session.get('pending_payment_id')
    print(f"🔵 pending_payment_id from session: {payment_id}")

    if not payment_id:
        print("⚠️ No pending_payment_id in session! Redirecting to payment options")
        flash('Please start a payment first', 'error')
        return redirect(url_for('payment_options'))

    payment = Payment.query.get(payment_id)
    print(f"🔵 Payment found: {payment}")

    if not payment:
        print(f"⚠️ Payment with ID {payment_id} not found in database!")
        session.pop('pending_payment_id', None)
        flash('Payment not found. Please try again.', 'error')
        return redirect(url_for('payment_options'))

    # Verify payment belongs to current user
    if payment.user_id != current_user.id:
        print(f"⚠️ Payment user mismatch! Payment user: {payment.user_id}, Current user: {current_user.id}")
        session.pop('pending_payment_id', None)
        abort(403)

    print(f"✅ Showing instructions for payment: {payment.transaction_id}")

    # ... rest of your instructions code ...

    # Instructions for each payment method
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

    # In a real system, you would verify payment with provider API
    # For demo, we'll simulate verification
    payment.status = 'completed'
    db.session.commit()

    # Clear session
    session.pop('pending_payment_id', None)

    return redirect(url_for('payment_success'))


@app.route('/payment-webhook/tnm', methods=['POST'])
def tnm_webhook():
    """Handle TNM payment callback"""
    data = request.json

    # Verify signature
    signature = request.headers.get('X-TNM-Signature')
    # Add signature verification logic

    transaction_id = data.get('transaction_id')
    status = data.get('status')

    # Find payment
    payment = Payment.query.filter_by(
        provider_reference=transaction_id,
        provider_name='tnm'
    ).first()

    if payment:
        if status == 'SUCCESS':
            payment.status = 'completed'
            payment.verified_at = datetime.utcnow()
        else:
            payment.status = 'failed'

        db.session.commit()

    return jsonify({'status': 'received'}), 200


@app.route('/payment-webhook/airtel', methods=['POST'])
def airtel_webhook():
    """Handle Airtel payment callback"""
    data = request.json

    # Verify the callback
    reference = data.get('reference')
    status = data.get('status')

    payment = Payment.query.filter_by(transaction_id=reference).first()

    if payment and status == 'SUCCESSFUL':
        payment.status = 'completed'
        payment.provider_name = 'airtel'
        payment.verified_at = datetime.utcnow()
        db.session.commit()

    return jsonify({'status': 'ok'}), 200


@app.route('/admin/view-proof/<int:payment_id>')
@admin_required
def view_payment_proof(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    return render_template('admin_view_proof.html', payment=payment)


@app.route('/admin/approve-payment/<int:payment_id>')
@admin_required
def approve_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'completed'
    payment.verified_by = current_user.id
    payment.verified_at = datetime.utcnow()
    db.session.commit()

    flash(f'Payment {payment.transaction_id} approved!', 'success')
    return redirect(url_for('admin_payments'))


@app.route('/admin/reject-payment/<int:payment_id>')
@admin_required
def reject_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'rejected'
    payment.verified_by = current_user.id
    payment.verified_at = datetime.utcnow()
    db.session.commit()

    flash(f'Payment {payment.transaction_id} rejected.', 'warning')
    return redirect(url_for('admin_payments'))


@app.route('/bursary-application')
@login_required
def bursary_application():
    return render_template('bursary_application.html')


@app.route('/confirm-payment-manual/<transaction_id>')
@login_required
def confirm_payment_manual(transaction_id):
    """Student confirms they've made payment"""
    payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()

    # Verify payment belongs to current user
    if payment.user_id != current_user.id:
        abort(403)

    return render_template('confirm_payment.html',
                           payment=payment,
                           transaction_id=transaction_id)


@app.route('/submit-proof/<transaction_id>', methods=['POST'])
@login_required
def submit_payment_proof(transaction_id):
    """Student submits payment proof (screenshot/receipt)"""
    payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()

    if payment.user_id != current_user.id:
        abort(403)

    # Save uploaded proof
    if 'payment_proof' in request.files:
        file = request.files['payment_proof']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"proof_{transaction_id}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'proofs', unique_filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            # Update payment with proof
            payment.proof_path = f"/static/uploads/proofs/{unique_filename}"
            payment.status = 'pending_verification'
            db.session.commit()

    flash('Payment proof submitted! We will verify it within 24 hours.', 'success')
    return redirect(url_for('dashboard'))


# Add to requirements.txt: requests==2.31.0
import requests
import time


def check_payment_status(payment_id):
    """Check if payment has been made (simulated)"""
    payment = Payment.query.get(payment_id)

    # In real system, you would call payment gateway API
    # For demo, we'll simulate verification

    # Simulate checking with provider
    if payment.provider_name == 'tnm':
        # Call TNM API
        # response = requests.get(f"https://api.tnm.co.mw/check/{payment.provider_reference}")
        # return response.json().get('status') == 'completed'
        pass

    return False


@app.route('/check-my-payments')
@login_required
def check_my_payments():
    """Student checks their payment status"""
    payments = Payment.query.filter_by(user_id=current_user.id) \
        .order_by(Payment.created_at.desc()).all()

    return render_template('my_payments.html', payments=payments)

@app.route('/submit-bursary', methods=['POST'])
@login_required
def submit_bursary():
    # Get form data
    bursary_type = request.form.get('bursary_type')
    student_id = request.form.get('student_id')
    guardian_name = request.form.get('guardian_name')
    guardian_phone = request.form.get('guardian_phone')
    reason = request.form.get('reason')

    # Create bursary payment
    payment = Payment(
        user_id=current_user.id,
        amount=0,
        currency='MWK',
        weeks=4,  # Default 4 weeks for bursary
        payment_method='Three Fold Bursary - ' + bursary_type,
        transaction_id=f"BURSARY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        status='pending_approval',  # Needs admin approval
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


# ============ SAMPLE RESOURCES ============
@app.route('/sample-resource/<subject_name>')
def sample_resource(subject_name):
    """Serve sample resources"""
    subject_resources = {
        'Mathematics': {
            'title': 'Algebra Basics Worksheet',
            'description': 'Practice problems covering algebraic expressions and equations',
            'type': 'pdf',
            'size': '2.1 MB'
        },
        'Chemistry': {
            'title': 'Periodic Table Guide',
            'description': 'Complete guide to chemical elements and their properties',
            'type': 'pdf',
            'size': '3.5 MB'
        },
        'Physics': {
            'title': 'Motion & Forces Problems',
            'description': 'Physics problems with step-by-step solutions',
            'type': 'pdf',
            'size': '1.8 MB'
        },
        'Agriculture': {
            'title': 'Soil Analysis Guide',
            'description': 'How to analyze and improve soil quality',
            'type': 'pdf',
            'size': '4.2 MB'
        },
        'Biology': {
            'title': 'Cell Structure Diagrams',
            'description': 'Detailed diagrams of plant and animal cells',
            'type': 'pdf',
            'size': '5.3 MB'
        },
        'English': {
            'title': 'Grammar Rules Handbook',
            'description': 'Complete guide to English grammar rules',
            'type': 'pdf',
            'size': '3.7 MB'
        },
        'Chichewa': {
            'title': 'Basic Chichewa Phrases',
            'description': 'Common phrases and vocabulary for beginners',
            'type': 'pdf',
            'size': '2.5 MB'
        },
        'Geography': {
            'title': 'Map Reading Guide',
            'description': 'How to read and interpret different types of maps',
            'type': 'pdf',
            'size': '4.8 MB'
        },
        'History': {
            'title': 'Malawi History Timeline',
            'description': 'Important events in Malawi history',
            'type': 'pdf',
            'size': '3.2 MB'
        }
    }

    resource = subject_resources.get(subject_name, {
        'title': 'Sample Resource',
        'description': 'Educational material',
        'type': 'pdf',
        'size': '1.0 MB'
    })

    return jsonify(resource)


# ============ ADMIN ROUTES ============
@app.route('/admin')
@admin_required
def admin():
    # Calculate stats
    total_users = User.query.count()
    total_subjects = Subject.query.count()
    total_enrollments = Enrollment.query.count()

    # Get today's registrations
    today = datetime.utcnow().date()
    today_registrations = User.query.filter(
        db.func.date(User.created_at) == today
    ).count()

    # Get active users (users with enrollments)
    active_users = db.session.query(db.func.count(db.func.distinct(Enrollment.user_id))).scalar()

    # Get pending payments
    pending_payments = Payment.query.filter(Payment.status.in_(['pending', 'pending_approval'])).count()
    pending_bursaries = Payment.query.filter_by(status='pending_approval').count()

    # Get total revenue
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
    # Get all users with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # Get today's count
    today = datetime.utcnow().date()
    today_count = User.query.filter(db.func.date(User.created_at) == today).count()

    return render_template('admin_users.html', users=users, today_count=today_count)


@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_user_detail(user_id):
    user = User.query.get_or_404(user_id)

    # Get user statistics
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

    # Get subject statistics
    total_lessons = Lesson.query.filter_by(subject_id=subject_id).count()
    total_enrollments = Enrollment.query.filter_by(subject_id=subject_id).count()

    return render_template('admin_subject_detail.html',
                           subject=subject,
                           total_lessons=total_lessons,
                           total_enrollments=total_enrollments)


@app.route('/admin/payments')
@admin_required
def admin_payments():
    # Get filter parameters
    status = request.args.get('status', 'all')
    method = request.args.get('method', 'all')

    query = Payment.query

    if status != 'all':
        query = query.filter_by(status=status)
    if method != 'all':
        query = query.filter_by(payment_method=method)

    # Get statistics for the header
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='completed').scalar() or 0
    pending_count = Payment.query.filter_by(status='pending_approval').count()

    # Today's payments
    today = datetime.utcnow().date()
    today_count = Payment.query.filter(
        db.func.date(Payment.created_at) == today
    ).count()

    # This month's revenue
    month_start = datetime.utcnow().replace(day=1)
    month_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'completed',
        Payment.created_at >= month_start
    ).scalar() or 0

    # Pagination
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

    # If approving bursary, set end date
    if old_status == 'pending_approval' and new_status == 'completed':
        payment.start_date = datetime.utcnow()
        payment.end_date = datetime.utcnow() + timedelta(weeks=payment.weeks)

    db.session.commit()

    flash(f'Payment status updated from {old_status} to {new_status}', 'success')
    return redirect(url_for('admin_payments'))


@app.route('/admin/lessons')
@admin_required
def admin_lessons():
    # Filter by subject if specified
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

            # Handle YouTube URLs
            if content_type == 'youtube':
                youtube_url = request.form.get('youtube_url', '')
                embed_url = request.form.get('embed_url', '')

                if youtube_url:
                    # Convert regular YouTube URL to embed URL
                    video_id = extract_youtube_id(youtube_url)
                    if video_id:
                        lesson.external_url = f"https://www.youtube.com/embed/{video_id}"
                    elif embed_url:
                        # Use provided embed URL for unlisted videos
                        lesson.external_url = embed_url
                    else:
                        lesson.external_url = youtube_url

            # Handle file upload
            elif 'file' in request.files and request.files['file'].filename:
                file = request.files['file']
                if file and allowed_file(file.filename):
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    lesson.file_path = f"/static/uploads/{unique_filename}"

                    # Set appropriate content type based on file extension
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


# Helper function to extract YouTube ID
def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    import re

    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'^([A-Za-z0-9_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    # Get daily registrations for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Daily user registrations
    daily_registrations = db.session.query(
        db.func.date(User.created_at).label('date'),
        db.func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago) \
        .group_by(db.func.date(User.created_at)) \
        .order_by('date') \
        .all()

    # Payment analytics
    payment_by_method = db.session.query(
        Payment.payment_method,
        db.func.count(Payment.id).label('count'),
        db.func.sum(Payment.amount).label('total')
    ).filter(Payment.status == 'completed') \
        .group_by(Payment.payment_method) \
        .all()

    # Enrollment by subject
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


# ============ INITIALIZE DATABASE ============
def init_database():
    with app.app_context():
        db.create_all()

        # Create admin user if not exists
        admin = User.query.filter_by(email='admin@threefoldventures.com').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                email='admin@threefoldventures.com',
                password=hashed_password,
                name='Administrator',
                phone='0888123456',
                is_admin=True
            )
            db.session.add(admin)

        # Check if subjects already exist
        if Subject.query.count() == 0:
            # Create all subjects
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

                # Demo video URLs for each subject
                demo_videos = {
                    'Mathematics': 'https://www.youtube.com/embed/Kp2bYWRQylk',
                    'Chemistry': 'https://www.youtube.com/embed/ulyopnxjAZ8',
                    'Physics': 'https://www.youtube.com/embed/D2FMV-2RwDk',
                    'Agriculture': 'https://www.youtube.com/embed/LqvcAs5PVWQ',
                    'Biology': 'https://www.youtube.com/embed/IBaXkgwi7kc',
                    'English': 'https://www.youtube.com/embed/s9shPouRWCs',
                    'Chichewa': 'https://www.youtube.com/embed/5Q98rYbOPag',
                    'Geography': 'https://www.youtube.com/embed/WwNuvGLblJU',
                    'History': 'https://www.youtube.com/embed/yqrR1dGqNp0'
                }

                subject_name = subj_data['name']
                video_url = demo_videos.get(subject_name, 'https://www.youtube.com/embed/dQw4w9WgXcQ')

                # Demo topics for each subject
                topics_map = {
                    'Mathematics': ['Algebra Basics', 'Geometry', 'Calculus', 'Statistics', 'Trigonometry'],
                    'Chemistry': ['Atomic Structure', 'Chemical Reactions', 'Organic Chemistry', 'Laboratory',
                                  'Periodic Table'],
                    'Physics': ['Motion', 'Energy', 'Electricity', 'Magnetism', 'Waves'],
                    'Agriculture': ['Soil Science', 'Crop Production', 'Animal Husbandry', 'Farm Management',
                                    'Sustainable Farming'],
                    'Biology': ['Cell Biology', 'Genetics', 'Human Anatomy', 'Ecology', 'Evolution'],
                    'English': ['Grammar', 'Essay Writing', 'Literature', 'Communication', 'Vocabulary'],
                    'Chichewa': ['Greetings', 'Grammar', 'Reading', 'Writing', 'Conversation'],
                    'Geography': ['Map Reading', 'Climate', 'Population', 'Economic', 'Environmental'],
                    'History': ['Ancient Civilizations', 'World Wars', 'African History', 'Malawi History',
                                'Modern History']
                }

                topics = topics_map.get(subject_name, ['Introduction', 'Basics', 'Intermediate', 'Advanced', 'Review'])

                # Create 20 lessons (4 weeks x 5 days)
                for week in range(1, 5):
                    for day in range(1, 6):
                        topic_index = (week - 1) * 5 + (day - 1)
                        topic = topics[topic_index % len(topics)]

                        lesson = Lesson(
                            subject=subject,
                            title=f"Week {week}, Day {day}: {topic}",
                            description=f"Learn about {topic.lower()} in {subject_name.lower()}. This lesson covers fundamental concepts and practical applications.",
                            week_number=week,
                            day_number=day,
                            content_type='video',
                            external_url=video_url,
                            duration=30 + (day * 5),  # 30-55 minutes
                            order=day,
                            is_published=True
                        )
                        db.session.add(lesson)

        db.session.commit()
        print("✅ THREE FOLD VENTURES database initialized with demo videos!")


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



# Add session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'tfv_'

@app.route('/setup-db')
def setup_database():
    """Initialize database tables and create admin user"""
    try:
        with app.app_context():
            db.create_all()
            init_database()
        return """
        <h1>Database Initialized Successfully!</h1>
        <p>✅ Tables created</p>
        <p>✅ Admin user created (admin@threefoldventures.com / admin123)</p>
        <p>✅ Demo subjects and lessons added</p>
        <p><a href="/">Go to Homepage</a></p>
        <p><strong>IMPORTANT:</strong> Remove this route after use!</p>
        """
    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

@app.route('/test-db')
def test_database():
    """Test database connection"""
    try:
        db.session.execute('SELECT 1')
        return "Database connected successfully!"
    except Exception as e:
        return f"Database error: {str(e)}"
        
# ============ RUN APPLICATION ============
# ============ RUN APPLICATION ============
if __name__ == '__main__':
    with app.app_context():
        init_database()

    # For Render deployment
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

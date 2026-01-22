# final_reset.py
import os
from app import app, db

print("🔄 COMPLETE DATABASE RESET...")

with app.app_context():
    # Get database path
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')

    # Delete database file
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Deleted: {db_path}")

    # Delete journal file
    journal_path = db_path + '-journal'
    if os.path.exists(journal_path):
        os.remove(journal_path)
        print(f"🗑️  Deleted: {journal_path}")

    # Drop all tables (clean slate)
    try:
        db.drop_all()
    except:
        pass

    # Create all tables with NEW schema
    db.create_all()
    print("✅ Created NEW database with correct schema")

    # Create admin user
    from app import User, Subject, Lesson
    from flask_bcrypt import Bcrypt
    from datetime import datetime

    bcrypt = Bcrypt(app)
    hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')

    admin = User(
        email='admin@threefoldventures.com',
        password=hashed_password,
        name='Administrator',
        phone='0888123456',
        is_admin=True
    )
    db.session.add(admin)

    # Create demo subjects
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

        # Create 2 demo lessons
        for i in range(1, 3):
            lesson = Lesson(
                subject=subject,
                title=f"Introduction to {subj_data['name']} - Part {i}",
                description=f"Learn basic concepts in {subj_data['name']}.",
                week_number=1,
                day_number=i,
                content_type='youtube',
                external_url='https://www.youtube.com/embed/Kp2bYWRQylk',
                duration=30,
                order=i,
                is_published=True
            )
            db.session.add(lesson)

    db.session.commit()

    print("\n" + "=" * 50)
    print("✅ DATABASE RESET COMPLETE!")
    print("=" * 50)
    print("\n👑 Admin Login:")
    print("   Email: admin@threefoldventures.com")
    print("   Password: admin123")
    print("\n🚀 Start with: python app.py")
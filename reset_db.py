# reset_db_fixed.py
import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app import app, db, User, Subject, Lesson
from flask_bcrypt import Bcrypt
from datetime import datetime


def reset_database():
    print("🔄 Resetting database...")

    with app.app_context():
        # Close any existing connections
        db.session.close_all()

        # Get the database file path from SQLAlchemy URI
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')

        # Delete database file if it exists
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"🗑️  Deleted old database: {db_path}")
            except Exception as e:
                print(f"⚠️  Could not delete {db_path}: {e}")
                print("Trying to continue anyway...")

        # Also delete journal file if exists
        journal_path = db_path + '-journal'
        if os.path.exists(journal_path):
            try:
                os.remove(journal_path)
                print(f"🗑️  Deleted journal file: {journal_path}")
            except:
                pass

        # Drop all tables (in case they exist in memory)
        try:
            db.drop_all()
        except:
            pass

        # Create all tables
        db.create_all()
        print("✅ Created new tables with updated schema")

        # Initialize Bcrypt
        bcrypt = Bcrypt(app)

        # Check if admin already exists
        admin = User.query.filter_by(email='admin@threefoldventures.com').first()
        if not admin:
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
            print("👑 Admin user created")
        else:
            print("👑 Admin user already exists")

        # Check if subjects already exist
        if Subject.query.count() == 0:
            print("📚 Creating demo subjects and lessons...")
            # Create subjects with unique codes
            subjects_data = [
                {'name': 'Mathematics', 'code': 'MATH001', 'icon': 'fas fa-calculator', 'color': '#3B82F6',
                 'description': 'Master mathematical concepts from basics to advanced topics'},
                {'name': 'Chemistry', 'code': 'CHEM002', 'icon': 'fas fa-flask', 'color': '#10B981',
                 'description': 'Learn chemical reactions, formulas, and laboratory techniques'},
                {'name': 'Physics', 'code': 'PHYS003', 'icon': 'fas fa-atom', 'color': '#EF4444',
                 'description': 'Understand the laws of motion, energy, and the physical world'},
                {'name': 'Agriculture', 'code': 'AGRI004', 'icon': 'fas fa-tractor', 'color': '#8B5CF6',
                 'description': 'Modern farming techniques and agricultural science'},
                {'name': 'Biology', 'code': 'BIOL005', 'icon': 'fas fa-dna', 'color': '#059669',
                 'description': 'Study of living organisms and life processes'},
                {'name': 'English', 'code': 'ENGL006', 'icon': 'fas fa-book', 'color': '#DC2626',
                 'description': 'Master English language, literature, and communication skills'},
                {'name': 'Chichewa', 'code': 'CHIC007', 'icon': 'fas fa-language', 'color': '#F59E0B',
                 'description': 'Malawi national language - reading, writing, and speaking'},
                {'name': 'Geography', 'code': 'GEOG008', 'icon': 'fas fa-globe-africa', 'color': '#6366F1',
                 'description': 'Study of Earth, landscapes, and human-environment interaction'},
                {'name': 'History', 'code': 'HIST009', 'icon': 'fas fa-landmark', 'color': '#8B5CF6',
                 'description': 'Explore historical events and their impact on modern society'},
            ]

            for subj_data in subjects_data:
                subject = Subject(**subj_data)
                db.session.add(subject)

                # Create 2 demo lessons for each subject (instead of 20 to keep it simple)
                for i in range(1, 3):
                    lesson = Lesson(
                        subject=subject,
                        title=f"Introduction to {subj_data['name']} - Part {i}",
                        description=f"Learn basic concepts in {subj_data['name']}. This lesson covers fundamental principles.",
                        week_number=1,
                        day_number=i,
                        content_type='youtube',
                        external_url='https://www.youtube.com/embed/Kp2bYWRQylk',
                        duration=30,
                        order=i,
                        is_published=True
                    )
                    db.session.add(lesson)

            print(f"✅ Created {len(subjects_data)} subjects with demo lessons")
        else:
            print("📚 Subjects already exist, skipping creation")

        # Commit everything
        db.session.commit()

        print("\n" + "=" * 50)
        print("🎉 DATABASE RESET COMPLETE!")
        print("=" * 50)
        print("\n📊 Stats:")
        print(f"   Users: {User.query.count()}")
        print(f"   Subjects: {Subject.query.count()}")
        print(f"   Lessons: {Lesson.query.count()}")
        print("\n🔑 Admin Login:")
        print("   Email: admin@threefoldventures.com")
        print("   Password: admin123")
        print("\n🚀 Start your app with: python app.py")


if __name__ == '__main__':
    reset_database()
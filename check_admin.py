# check_admin.py
from app import app, db, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

with app.app_context():
    print("=== CHECKING ADMIN USER ===")

    # Check all users
    all_users = User.query.all()
    print(f"Total users: {len(all_users)}")

    for user in all_users:
        print(f"User: {user.email}, Admin: {user.is_admin}, Active: {user.is_active}")

    # Check specifically for admin@threefoldventures.com
    admin_user = User.query.filter_by(email='admin@threefoldventures.com').first()
    if admin_user:
        print(f"\n✓ Admin user found: {admin_user.email}")
        print(f"  Is admin: {admin_user.is_admin}")
        print(f"  Is active: {user.is_active}")
    else:
        print("\n✗ Admin user NOT found!")
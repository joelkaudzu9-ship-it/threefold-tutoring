#!/usr/bin/env python3
"""
Start the tutoring platform prototype
"""
import subprocess
import sys
import os


def install_dependencies():
    print("📦 Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])


def check_python_version():
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher required")
        sys.exit(1)


def create_env_file():
    if not os.path.exists('.env'):
        print("🔑 Creating .env file with test keys...")
        with open('.env', 'w') as f:
            f.write("""FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-later
STRIPE_PUBLIC_KEY=pk_test_51Nexample
STRIPE_SECRET_KEY=sk_test_51Nexample
""")
        print("✅ Created .env file")


def main():
    print("🚀 Starting Online Tutoring Platform Prototype")
    print("=" * 50)

    # Check Python
    check_python_version()

    # Install dependencies
    try:
        install_dependencies()
    except:
        print("⚠️  Could not install dependencies automatically")
        print("📋 Please run: pip install -r requirements.txt")

    # Create .env file
    create_env_file()

    # Create necessary directories
    os.makedirs('static/uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)

    print("\n✅ Setup complete!")
    print("\n📋 To start the server:")
    print("   1. python app.py")
    print("\n🌐 Then open: http://localhost:5000")
    print("\n🔑 Default login:")
    print("   Email: admin@tutoring.com")
    print("   Password: admin123")
    print("\n💳 Test payment with card: 4242 4242 4242 4242")


if __name__ == '__main__':
    main()
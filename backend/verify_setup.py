#!/usr/bin/env python
"""
Verification script to test that the backend is set up correctly.
Run this after installing dependencies to verify everything works.
"""

import sys


def check_imports():
    """Check that all required packages can be imported."""
    print("Checking imports...")
    required_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("alembic", "Alembic"),
        ("pydantic", "Pydantic"),
    ]

    failed = []
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name}")
            failed.append(name)

    if failed:
        print(f"\n❌ Missing packages: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False

    print("✓ All required packages installed\n")
    return True


def check_app():
    """Check that the FastAPI app can be created."""
    print("Checking FastAPI app...")
    try:
        from app.main import app
        from app.config import settings

        print(f"  ✓ App created: {settings.app_name} v{settings.app_version}")
        print(f"  ✓ Database URL: {settings.database_url}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to create app: {e}")
        return False


def check_models():
    """Check that all models can be imported."""
    print("\nChecking database models...")
    try:
        from app.models import (
            User,
            Campaign,
            Character,
            Item,
            Spell,
        )

        models = [
            ("User", User),
            ("Campaign", Campaign),
            ("Character", Character),
            ("Item", Item),
            ("Spell", Spell),
        ]

        for name, model in models:
            print(f"  ✓ {name} model")

        return True
    except Exception as e:
        print(f"  ✗ Failed to import models: {e}")
        return False


def check_database():
    """Check that database can be created."""
    print("\nChecking database connection...")
    try:
        from app.database import engine, Base
        from app.models import User, Campaign, Character, Item, Spell

        # Create tables
        Base.metadata.create_all(bind=engine)
        print("  ✓ Database tables created successfully")

        # Try a simple query
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            count = session.query(User).count()
            print(f"  ✓ Database query successful (users: {count})")

        return True
    except Exception as e:
        print(f"  ✗ Database check failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("OSE Sheets Backend - Setup Verification")
    print("=" * 60)
    print()

    checks = [
        check_imports(),
        check_app(),
        check_models(),
        check_database(),
    ]

    print("\n" + "=" * 60)
    if all(checks):
        print("✓ All checks passed! Your setup is ready.")
        print("\nNext steps:")
        print("  1. Run: uvicorn app.main:app --reload")
        print("  2. Visit: http://localhost:8000/api/docs")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

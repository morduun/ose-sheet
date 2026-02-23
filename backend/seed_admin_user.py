#!/usr/bin/env python
"""Create an admin user for testing."""

from app.database import SessionLocal
from app.models import User

def main():
    db = SessionLocal()

    admin_user = db.query(User).filter(User.email == "admin@example.com").first()

    if admin_user:
        if not admin_user.is_admin:
            admin_user.is_admin = True
            db.commit()
            print("✓ Updated existing user to admin")
        else:
            print("✓ Admin user already exists")
    else:
        admin_user = User(
            google_id="admin-test-google-id",
            email="admin@example.com",
            name="Admin User",
            is_admin=True
        )
        db.add(admin_user)
        db.commit()
        print("✓ Created new admin user")

    print(f"   Email: {admin_user.email}")
    print(f"   ID: {admin_user.id}")

    db.close()

if __name__ == "__main__":
    main()

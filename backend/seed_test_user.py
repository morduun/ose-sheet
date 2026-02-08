#!/usr/bin/env python
"""Seed a test user for Phase 1 testing."""

from app.database import SessionLocal
from app.models import User

db = SessionLocal()

# Check if user already exists
existing_user = db.query(User).filter(User.id == 1).first()
if not existing_user:
    user = User(
        id=1,
        google_id="test-google-id",
        email="test@example.com",
        name="Test User"
    )
    db.add(user)
    db.commit()
    print("✓ Created test user (ID: 1, email: test@example.com)")
else:
    print("✓ Test user already exists")

db.close()

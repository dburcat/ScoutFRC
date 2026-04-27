#!/usr/bin/env python3
"""
check_admin.py — Diagnose login issues and optionally reset the admin password.

Usage:
    cd backend
    python scripts/check_admin.py
"""
from __future__ import annotations

import sys
import warnings
import logging

warnings.filterwarnings("ignore")
logging.getLogger("passlib").setLevel(logging.ERROR)

from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.db.session import SessionLocal
from app.models import User
from app.core.security import get_password_hash, verify_password


def main() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).all()

        print()
        print("Users in database:")
        print("─" * 50)
        if not users:
            print("  No users found — run init_admin.py first")
            return

        for u in users:
            print(f"  id={u.user_id}  username='{u.username}'  role={u.role}  active={u.is_active}")
            print(f"  hash={u.hashed_password[:40]}…")
            print()

        # Test password verification interactively
        username = input("Enter username to test: ").strip()
        password = input("Enter password to test: ").strip()

        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"  ✗ No user '{username}' found in DB")
            return

        result = verify_password(password, user.hashed_password)
        print(f"  verify_password result: {result}")

        if not result:
            print()
            print("Password does not match. Resetting it now…")
            user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"  ✓ Password updated for '{username}'")
            print(f"  ✓ Re-testing… {verify_password(password, user.hashed_password)}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
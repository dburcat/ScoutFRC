#!/usr/bin/env python3
"""
init_admin.py — Clean database and create the admin user.

Usage:
    cd backend
    python scripts/init_admin.py
"""
from __future__ import annotations

import sys
import warnings
import logging
from pathlib import Path

# Suppress the passlib/bcrypt version warning before any imports trigger it
warnings.filterwarnings("ignore", ".*error reading bcrypt version.*")
logging.getLogger("passlib").setLevel(logging.ERROR)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text
from app.db.database import engine
from app.db.session import SessionLocal
from app.models import User
from app.core.security import get_password_hash

TRUNCATE_SQL = """
    TRUNCATE TABLE
        scouting_observation,
        sync_log,
        robot_performance,
        alliance,
        "match",
        event,
        team,
        "user"
    RESTART IDENTITY CASCADE
"""


def wipe_database() -> None:
    print("Wiping all application data…")
    with engine.begin() as conn:
        conn.execute(text(TRUNCATE_SQL))
    print("  ✓ All tables cleared")


def create_admin(username: str, password: str) -> User:
    db = SessionLocal()
    try:
        user = User(
            username=username,
            email=f"{username}@scouterfrc.local",
            hashed_password=get_password_hash(password),
            team_id=None,
            role="SYSTEM_ADMIN",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def prompt_credentials() -> tuple[str, str]:
    print()
    print("Create admin account")
    print("─" * 30)
    print("Note: password input is hidden — characters won't appear as you type.")
    print()

    username = input("Username [admin]: ").strip() or "admin"

    while True:
        # Use input() instead of getpass() to avoid terminal hiding issues
        password = input("Password (min 8 chars): ").strip()
        if not password:
            print("  ✗ Password cannot be empty")
            continue
        if len(password) < 8:
            print("  ✗ Password must be at least 8 characters")
            continue
        confirm = input("Confirm password: ").strip()
        if password != confirm:
            print("  ✗ Passwords do not match, try again")
            continue
        break

    return username, password


def main() -> None:
    print()
    print("ScouterFRC — Database initialisation")
    print("=" * 40)
    print()
    print("⚠️  This will WIPE all existing data from the database.")
    confirm = input("Type 'yes' to continue: ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    wipe_database()

    username, password = prompt_credentials()

    print()
    print("Creating admin user…")
    user = create_admin(username, password)
    print(f"  ✓ Created '{user.username}' (id={user.user_id}, role=SYSTEM_ADMIN)")

    print()
    print("=" * 40)
    print("Done! Next steps:")
    print(f"  1. Start the backend:  uvicorn app.main:app --reload")
    print(f"  2. Log in with username '{username}'")
    print(f"  3. Use TBA Sync in the sidebar — enter e.g. '2026' to bootstrap")
    print()


if __name__ == "__main__":
    main()
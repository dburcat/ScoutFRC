from __future__ import annotations

from collections.abc import Generator
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models import Base, User
from app.main import app


engine = create_engine(settings.DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True, class_=Session)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user with SCOUT role"""
    user = User(
        email="scout@test.com",
        username="testscout",
        hashed_password=get_password_hash("testpass123"),
        role="SCOUT",
        team_id=1,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    """Create a test admin user"""
    user = User(
        email="admin@test.com",
        username="testadmin",
        hashed_password=get_password_hash("adminpass123"),
        role="SYSTEM_ADMIN",
        team_id=None,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user) -> str:
    """Generate auth token for test user"""
    return create_access_token(
        subject=test_user.user_id,
        expires_delta=timedelta(days=1)
    )


@pytest.fixture
def admin_token(admin_user) -> str:
    """Generate auth token for admin user"""
    return create_access_token(
        subject=admin_user.user_id,
        expires_delta=timedelta(days=1)
    )


@pytest.fixture
def client_with_auth(test_user_token) -> TestClient:
    """TestClient with auth header for test user"""
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {test_user_token}"})
    return client


@pytest.fixture
def admin_client(admin_token) -> TestClient:
    """TestClient with auth header for admin user"""
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return client
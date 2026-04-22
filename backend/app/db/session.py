from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True, class_=Session)

def get_db():
    db = SessionLocal() # This should be your sessionmaker
    try:
        yield db
    finally:
        db.close()
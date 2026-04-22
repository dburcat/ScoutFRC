from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from db.database import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True, class_=Session)


def get_session() -> Session:
	return SessionLocal()

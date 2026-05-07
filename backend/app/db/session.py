from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine

_SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True, class_=Session)


class _SessionLocal:
    """
    Drop-in replacement that supports both call syntax and context manager syntax:
        db = SessionLocal()          # plain call - caller must close manually
        with SessionLocal() as db:   # context manager - auto-closed on exit
    """

    def __call__(self) -> Session:
        return _SessionFactory()

    def __enter__(self) -> Session:
        self._session = _SessionFactory()
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._session.close()


SessionLocal = _SessionLocal()


def get_db():
    db = _SessionFactory()
    try:
        yield db
    finally:
        db.close()
"""
Database engine and session management using SQLAlchemy 2.x.
Provides connection pooling and session factory for the application.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from src.lib.settings import settings


# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create engine with connection pooling
# For async support later, use create_async_engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10,
)


# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes to get a database session.
    
    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI routes.
    
    Usage:
        with get_db_context() as db:
            result = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    Should be called after all models are imported.
    """
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all tables. Use with caution - for testing only.
    """
    Base.metadata.drop_all(bind=engine)

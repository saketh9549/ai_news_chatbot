from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_sync_engine = None
_sync_session_factory = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        db_url = settings.database_url_sync or ""
        
        if db_url.startswith("sqlite"):
            _sync_engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False, "timeout": 30},
                echo=False,
                pool_pre_ping=True,
            )
            
            # Attach SQLite-specific PRAGMAs ONLY to SQLite engines
            @event.listens_for(_sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                try:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA busy_timeout=10000")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.close()
                except Exception:
                    pass
        else:
            # PostgreSQL / Supabase configuration
            _sync_engine = create_engine(
                db_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False,
            )

        from app.db.models import Base
        Base.metadata.create_all(_sync_engine)
        
    return _sync_engine


def get_sync_session_factory():
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _sync_session_factory


def get_sync_session():
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()

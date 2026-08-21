from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_sync_engine = None
_sync_session_factory = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(settings.database_url_sync, echo=False)
        from app.db.models import Base
        Base.metadata.create_all(_sync_engine)
    return _sync_engine


def get_sync_session_factory():
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(get_sync_engine(), class_=Session, expire_on_commit=False)
    return _sync_session_factory


def get_sync_session():
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()

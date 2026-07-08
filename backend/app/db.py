from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from app.config import settings


engine = create_engine(
    settings.database_url.replace("sqlite+aiosqlite:///", "sqlite:///"),
    echo=False,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(engine, class_=Session, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    from app.services.workspace import get_or_create_default_workspace
    db = SessionLocal()
    try:
        get_or_create_default_workspace(db)
    finally:
        db.close()

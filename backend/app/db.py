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
    # Import all models so DeclarativeBase metadata is fully populated
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()
    from app.services.workspace import get_or_create_default_workspace
    db = SessionLocal()
    try:
        get_or_create_default_workspace(db)
    finally:
        db.close()


def _migrate_add_missing_columns() -> int:
    """Auto-add columns that exist in model metadata but not in the database.

    Only adds nullable columns — never touches existing columns, renames, drops,
    type changes, or constraints.  This keeps the develop-against-SQLite workflow
    self-healing (no manual DB drop / no Alembic) for the common additive case.

    Non-nullable additions are skipped with a warning: those need a manual
    migration or a dev-DB rebuild, since SQLite ADD COLUMN NOT NULL needs a
    default we can't always synthesize from a Python-side default.

    Returns the number of ALTER statements executed.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    altered = 0

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        missing = [c for c in table.columns if c.name not in existing]
        if not missing:
            continue

        with engine.begin() as conn:
            for col in missing:
                if not col.nullable:
                    print(f"[migrate] SKIP {table.name}.{col.name} — NOT NULL add needs manual migration / DB rebuild")
                    continue
                col_type = col.type.compile(dialect=engine.dialect)
                stmt = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
                print(f"[migrate] {stmt}")
                conn.execute(text(stmt))
                altered += 1

    if altered:
        print(f"[migrate] Applied {altered} missing column(s).")
    return altered

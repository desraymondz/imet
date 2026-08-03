# SQLAlchemy engine and session for the PostgreSQL database

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

# Shared connection pool, drop stale connections, log SQL
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)

# Factory for each request, requires db.commit(), disable autoflush
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass


def get_db():
    """Open a database session, yield it to the route, and close it when the request is done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Database connection check. Used by /health to verify if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def init_db():
    """Initialise the database tables and extensions."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create tables for a fresh database
    Base.metadata.create_all(bind=engine)
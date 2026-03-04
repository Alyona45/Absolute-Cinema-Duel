from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.settings import DATABASE_URL

# Re-export Base from models so the rest of the app can import it from here
from backend.models import Base  # noqa: F401

# Create the SQLAlchemy engine — the core interface to the database
# echo=False means SQL statements won't be printed to stdout
engine = create_engine(DATABASE_URL, echo=False)

# Session factory — each request will get its own session instance
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI routes.
    Yields a database session and ensures it is closed after the request.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

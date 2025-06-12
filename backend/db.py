"""Database engine and session setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ENGINE = create_engine("sqlite:///project.db", echo=False, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


def get_session():
    """Yield a new SQLAlchemy session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

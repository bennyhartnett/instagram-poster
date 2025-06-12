"""SQLAlchemy models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Video(Base):
    """Video record."""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    sha256 = Column(String, unique=True, nullable=False)
    title = Column(String, default="")
    description = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime)
    posted_at = Column(DateTime)
    insta_media_id = Column(String)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    last_error = Column(String)
    is_active = Column(Boolean, default=True)

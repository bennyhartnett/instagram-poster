from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

import pytest
from backend.models import Base, Video


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_video_insert_and_retrieve():
    session = create_session()
    vid = Video(file_path="video.mp4", sha256="abc")
    session.add(vid)
    session.commit()

    fetched = session.query(Video).filter_by(sha256="abc").one()
    assert fetched.file_path == "video.mp4"
    assert fetched.sha256 == "abc"


def test_unique_constraints():
    session = create_session()
    session.add(Video(file_path="dup.mp4", sha256="same"))
    session.commit()
    session.add(Video(file_path="dup.mp4", sha256="same"))
    with pytest.raises(IntegrityError):
        session.commit()

from datetime import datetime, timedelta
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import watcher
from backend.models import Base, Video


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.settings = {"timezone": "UTC"}
    return session


def test_on_created_adds_video(tmp_path):
    session = create_session()
    file_path = tmp_path / "test.mp4"
    file_path.write_text("data")

    handler = watcher.FolderHandler(session)
    event = SimpleNamespace(src_path=str(file_path), is_directory=False)
    handler.on_created(event)

    videos = session.query(Video).all()
    assert len(videos) == 1
    assert videos[0].file_path == str(file_path)

    # Duplicate file should not add another record
    handler.on_created(event)
    assert session.query(Video).count() == 1

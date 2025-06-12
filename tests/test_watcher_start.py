from backend import watcher
from backend.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


class DummyObserver:
    def __init__(self):
        self.scheduled = []
        self.daemon = False
        self.started = False

    def schedule(self, handler, path, recursive=False):
        self.scheduled.append((handler, path, recursive))

    def start(self):
        self.started = True


def test_start_watcher_monkeypatch(monkeypatch, tmp_path):
    session = create_session()
    dummy = DummyObserver()
    monkeypatch.setattr(watcher, "Observer", lambda: dummy)

    obs = watcher.start_watcher(str(tmp_path), session)
    assert obs is dummy
    assert dummy.started
    assert dummy.daemon
    assert dummy.scheduled[0][1] == str(tmp_path)

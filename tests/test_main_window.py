import os
import pytest

try:
    from PySide6 import QtWidgets
    from gui.main_window import MainWindow
    from backend.models import Base, Video
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except Exception:  # pragma: no cover - missing Qt deps
    QtWidgets = None


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


@pytest.mark.skipif(QtWidgets is None, reason="PySide6 not available")
def test_main_window_load_and_delete(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    session = create_session()
    video = Video(file_path=str(tmp_path / "a.mp4"), sha256="x", title="Vid")
    session.add(video)
    session.commit()

    monkeypatch.setattr('send2trash.send2trash', lambda p: None)

    win = MainWindow(session, scheduler=None)
    win.load_videos()
    assert win.tree.topLevelItemCount() == 1

    item = win.tree.topLevelItem(0)
    win.tree.setCurrentItem(item)
    win.delete_selected()

    assert session.get(Video, video.id).is_active is False

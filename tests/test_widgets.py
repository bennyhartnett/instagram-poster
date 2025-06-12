import pytest

try:
    from PySide6 import QtGui
    from gui.widgets import _generate_thumbnail
    import ffmpeg
except Exception:  # pragma: no cover - missing Qt deps
    QtGui = None


@pytest.mark.skipif(QtGui is None, reason="PySide6 not available")
def test_generate_thumbnail_handles_error(monkeypatch, tmp_path):
    dummy = tmp_path / "vid.mp4"
    dummy.write_text("data")

    class Dummy:
        def output(self, *a, **k):
            return self
        def overwrite_output(self):
            return self
        def run(self, quiet=True):
            raise RuntimeError

    monkeypatch.setattr(ffmpeg, "input", lambda *a, **k: Dummy())

    pixmap = _generate_thumbnail(str(dummy))
    assert isinstance(pixmap, QtGui.QPixmap)

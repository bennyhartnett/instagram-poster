"""Custom widgets used in the GUI."""
from __future__ import annotations

import os
import tempfile

from PySide6 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets

import ffmpeg


class _DBLineEdit(QtWidgets.QLineEdit):
    """QLineEdit that commits changes to the DB on focus loss."""

    def __init__(self, video, session, attr, parent=None):
        super().__init__(parent)
        self.video = video
        self.session = session
        self.attr = attr
        self.setText(getattr(video, attr) or "")
        self.editingFinished.connect(self._save)

    def _save(self) -> None:
        setattr(self.video, self.attr, self.text())
        self.session.commit()


class _DBTextEdit(QtWidgets.QTextEdit):
    """QTextEdit that commits changes to the DB on focus loss."""

    def __init__(self, video, session, attr, parent=None):
        super().__init__(parent)
        self.video = video
        self.session = session
        self.attr = attr
        self.setPlainText(getattr(video, attr) or "")

    def focusOutEvent(self, event) -> None:  # type: ignore[override]
        setattr(self.video, self.attr, self.toPlainText())
        self.session.commit()
        super().focusOutEvent(event)


class VideoItemWidget(QtWidgets.QWidget):
    """Widget representing a single video entry with preview and playback."""

    def __init__(self, video, session, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self.video = video
        self.session = session

        layout = QtWidgets.QHBoxLayout(self)

        self.thumb = QtWidgets.QLabel()
        self.thumb.setFixedSize(160, 90)
        self.thumb.setScaledContents(True)
        pix = _generate_thumbnail(video.file_path)
        if not pix.isNull():
            self.thumb.setPixmap(pix)
        layout.addWidget(self.thumb)

        form = QtWidgets.QVBoxLayout()
        self.edit_title = _DBLineEdit(video, session, "title")
        form.addWidget(self.edit_title)
        self.edit_desc = _DBTextEdit(video, session, "description")
        form.addWidget(self.edit_desc)
        layout.addLayout(form, 1)

        self.btn_play = QtWidgets.QPushButton("Play")
        self.btn_play.clicked.connect(self._open_player)
        layout.addWidget(self.btn_play)

    # ------------------------------------------------------------------
    def _open_player(self) -> None:
        dlg = _PlayerDialog(self.video.file_path, self)
        dlg.exec()


def _generate_thumbnail(video_path: str) -> QtGui.QPixmap:
    """Return a QPixmap thumbnail for the given video path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    try:
        (
            ffmpeg.input(video_path, ss=1)
            .output(tmp.name, vframes=1)
            .overwrite_output()
            .run(quiet=True)
        )
        pix = QtGui.QPixmap(tmp.name)
    except Exception:
        pix = QtGui.QPixmap()
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
    return pix


class _PlayerDialog(QtWidgets.QDialog):
    """Simple dialog with QMediaPlayer for preview."""

    def __init__(self, video_path: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Preview")

        layout = QtWidgets.QVBoxLayout(self)

        self.player = QtMultimedia.QMediaPlayer(self)
        video_widget = QtMultimediaWidgets.QVideoWidget(self)
        self.player.setVideoOutput(video_widget)
        self.player.setSource(QtCore.QUrl.fromLocalFile(video_path))
        layout.addWidget(video_widget)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.player.play()

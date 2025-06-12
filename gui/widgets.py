"""Custom widgets used in the GUI."""
from PySide6 import QtWidgets


class VideoItemWidget(QtWidgets.QWidget):
    """Widget representing a single video entry."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(title))
        # TODO: add thumbnail preview and play button using QMediaPlayer

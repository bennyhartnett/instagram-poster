"""Custom widgets used in the GUI."""
from PySide6 import QtWidgets


class VideoItemWidget(QtWidgets.QWidget):
    """Placeholder widget representing a video entry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Video item"))

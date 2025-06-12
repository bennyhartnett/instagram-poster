"""Main application window."""
from PySide6 import QtWidgets


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, session, scheduler, parent=None):
        super().__init__(parent)
        self.session = session
        self.scheduler = scheduler
        self.setWindowTitle("Instagram Scheduler")
        label = QtWidgets.QLabel("Instagram Scheduler", self)
        label.setAlignment(QtWidgets.Qt.AlignCenter)
        self.setCentralWidget(label)

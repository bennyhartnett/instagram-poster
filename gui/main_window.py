"""Main application window."""
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from backend.models import Video
from backend.instagram import post_to_instagram
from .schedule_dialog import ScheduleDialog
from .widgets import VideoItemWidget


class MainWindow(QtWidgets.QMainWindow):
    """Very small GUI showcasing the core workflow."""

    def __init__(self, session, scheduler, parent=None):
        super().__init__(parent)
        self.session = session
        self.scheduler = scheduler

        self.setWindowTitle("Instagram Scheduler")
        self.resize(800, 600)

        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(["Video", "Status", "Scheduled", "Posted"])
        layout.addWidget(self.tree)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_schedule = QtWidgets.QPushButton("Schedule")
        self.btn_post_now = QtWidgets.QPushButton("Post Now")
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_schedule)
        btn_layout.addWidget(self.btn_post_now)
        layout.addLayout(btn_layout)

        self.btn_refresh.clicked.connect(self.load_videos)
        self.btn_schedule.clicked.connect(self.schedule_selected)
        self.btn_post_now.clicked.connect(self.post_selected)

        self.load_videos()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def load_videos(self) -> None:
        """Populate the tree widget with current videos."""
        self.tree.clear()
        videos = self.session.query(Video).filter_by(is_active=True).all()
        for video in videos:
            status = (
                "Posted"
                if video.posted_at
                else ("Scheduled" if video.scheduled_at else "Unscheduled")
            )
            item = QtWidgets.QTreeWidgetItem([
                "",
                status,
                str(video.scheduled_at) if video.scheduled_at else "",
                str(video.posted_at) if video.posted_at else "",
            ])
            item.setData(0, QtCore.Qt.UserRole, video.id)
            self.tree.addTopLevelItem(item)
            widget = VideoItemWidget(video, self.session)
            self.tree.setItemWidget(item, 0, widget)

    def _current_video(self) -> Video | None:
        item = self.tree.currentItem()
        if not item:
            return None
        vid_id = item.data(0, QtCore.Qt.UserRole)
        return self.session.get(Video, vid_id)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def schedule_selected(self) -> None:
        video = self._current_video()
        if not video:
            return
        dlg = ScheduleDialog(video.scheduled_at, self)
        if dlg.exec():
            video.scheduled_at = dlg.scheduled_at
            self.session.commit()
            self.load_videos()

    def post_selected(self) -> None:
        video = self._current_video()
        if not video:
            return
        try:
            post_to_instagram(self.session, video)
            video.posted_at = datetime.utcnow()
            self.session.commit()
        except Exception as exc:  # pragma: no cover - network errors
            video.last_error = str(exc)
            self.session.commit()
            QtWidgets.QMessageBox.warning(self, "Error", str(exc))
        self.load_videos()


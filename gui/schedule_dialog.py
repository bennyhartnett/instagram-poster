"""Dialog for setting a video's scheduled time."""
from datetime import datetime

from PySide6 import QtCore, QtWidgets


class ScheduleDialog(QtWidgets.QDialog):
    """Simple datetime picker dialog."""

    def __init__(self, scheduled_at: datetime | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Video")

        layout = QtWidgets.QVBoxLayout(self)

        self.dt = QtWidgets.QDateTimeEdit(self)
        self.dt.setCalendarPopup(True)
        if scheduled_at:
            self.dt.setDateTime(QtCore.QDateTime.fromPython(scheduled_at))
        else:
            self.dt.setDateTime(QtCore.QDateTime.currentDateTime())
        layout.addWidget(self.dt)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    @property
    def scheduled_at(self) -> datetime:
        return self.dt.dateTime().toPython()

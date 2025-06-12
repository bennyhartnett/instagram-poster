"""Dialog for setting a video's scheduled time."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from PySide6 import QtCore, QtWidgets


class ScheduleDialog(QtWidgets.QDialog):
    """Simple datetime picker dialog."""

    def __init__(self, scheduled_at: datetime | None, tz: ZoneInfo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Video")
        self.tz = tz

        layout = QtWidgets.QVBoxLayout(self)

        self.dt = QtWidgets.QDateTimeEdit(self)
        self.dt.setCalendarPopup(True)
        if scheduled_at:
            local_dt = scheduled_at.replace(tzinfo=timezone.utc).astimezone(self.tz)
            self.dt.setDateTime(QtCore.QDateTime.fromPython(local_dt))
        else:
            self.dt.setDateTime(QtCore.QDateTime.fromPython(datetime.now(self.tz)))
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
        local_dt = self.dt.dateTime().toPython()
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=self.tz)
        else:
            local_dt = local_dt.astimezone(self.tz)
        utc_dt = local_dt.astimezone(timezone.utc)
        return utc_dt.replace(tzinfo=None)

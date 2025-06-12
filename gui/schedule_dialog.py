"""Dialog for editing the daily posting schedule template."""
from __future__ import annotations

from datetime import time
from typing import Iterable, List

from PySide6 import QtCore, QtWidgets


class ScheduleDialog(QtWidgets.QDialog):
    """Table-based editor for daily posting times."""

    def __init__(self, template: Iterable[time] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schedule Template")

        layout = QtWidgets.QVBoxLayout(self)

        self.table = QtWidgets.QTableWidget(25, 2, self)
        self.table.setHorizontalHeaderLabels(["Active", "Time"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        for row in range(25):
            chk = QtWidgets.QCheckBox()
            self.table.setCellWidget(row, 0, chk)
            t_edit = QtWidgets.QTimeEdit(QtCore.QTime(8, 0))
            t_edit.setDisplayFormat("HH:mm")
            self.table.setCellWidget(row, 1, t_edit)

        if template:
            for row, t in enumerate(template):
                if row >= 25:
                    break
                chk = self.table.cellWidget(row, 0)
                t_edit = self.table.cellWidget(row, 1)
                chk.setChecked(True)
                t_edit.setTime(QtCore.QTime(t.hour, t.minute))

        layout.addWidget(self.table)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    @property
    def schedule_template(self) -> List[time]:
        """Return checked times sorted ascending."""
        times: List[time] = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            t_edit = self.table.cellWidget(row, 1)
            if isinstance(chk, QtWidgets.QCheckBox) and chk.isChecked():
                qtime = t_edit.time() if isinstance(t_edit, QtWidgets.QTimeEdit) else QtCore.QTime(0, 0)
                times.append(qtime.toPython())
        times.sort()
        return times

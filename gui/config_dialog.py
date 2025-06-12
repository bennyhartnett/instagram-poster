from __future__ import annotations

"""Configuration dialog for adjusting app settings."""
from pathlib import Path
import json

from PySide6 import QtWidgets
import keyring
import pytz


class ConfigDialog(QtWidgets.QDialog):
    """Dialog to edit application settings."""

    def __init__(self, settings: dict, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._settings = settings

        layout = QtWidgets.QFormLayout(self)

        # Watch folder field with browse button
        watch_layout = QtWidgets.QHBoxLayout()
        self.edit_watch = QtWidgets.QLineEdit(settings.get("watch_folder", ""))
        self.btn_browse = QtWidgets.QPushButton("...")
        self.btn_browse.clicked.connect(self._choose_folder)
        watch_layout.addWidget(self.edit_watch, 1)
        watch_layout.addWidget(self.btn_browse)
        layout.addRow("Watch Folder", watch_layout)

        self.edit_user = QtWidgets.QLineEdit(settings.get("instagram_user_id", ""))
        layout.addRow("Instagram User ID", self.edit_user)

        token = keyring.get_password("ig_scheduler", "long_lived_token") or ""
        self.edit_token = QtWidgets.QLineEdit(token)
        self.edit_token.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("Long-lived Token", self.edit_token)

        self.spin_max = QtWidgets.QSpinBox()
        self.spin_max.setRange(0, 25)
        self.spin_max.setValue(settings.get("max_posts_per_day", 25))
        layout.addRow("Max posts / day", self.spin_max)

        self.spin_refresh = QtWidgets.QSpinBox()
        self.spin_refresh.setRange(5, 120)
        self.spin_refresh.setValue(settings.get("metrics_refresh_minutes", 30))
        layout.addRow("Metrics refresh minutes", self.spin_refresh)

        self.combo_tz = QtWidgets.QComboBox()
        self.combo_tz.addItem("")
        self.combo_tz.addItems(pytz.all_timezones)
        tz = settings.get("timezone", "")
        idx = self.combo_tz.findText(tz)
        if idx != -1:
            self.combo_tz.setCurrentIndex(idx)
        layout.addRow("Time-zone override", self.combo_tz)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    # ------------------------------------------------------------------
    def _choose_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Watch Folder", self.edit_watch.text() or str(Path.home())
        )
        if folder:
            self.edit_watch.setText(folder)

    # ------------------------------------------------------------------
    def save(self) -> dict:
        """Return updated settings and persist token via keyring."""
        keyring.set_password(
            "ig_scheduler", "long_lived_token", self.edit_token.text()
        )
        data = {
            "watch_folder": self.edit_watch.text(),
            "instagram_user_id": self.edit_user.text(),
            "max_posts_per_day": self.spin_max.value(),
            "metrics_refresh_minutes": self.spin_refresh.value(),
            "timezone": self.combo_tz.currentText(),
        }
        self._settings.update(data)
        with open("settings.json", "w") as f:
            json.dump(self._settings, f, indent=4)
        return data

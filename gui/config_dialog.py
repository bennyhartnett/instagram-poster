from PySide6 import QtWidgets


class ConfigDialog(QtWidgets.QDialog):
    """Small dialog for modifying application settings."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        layout = QtWidgets.QFormLayout(self)

        self.spin_max_posts = QtWidgets.QSpinBox()
        self.spin_max_posts.setRange(0, 25)
        self.spin_max_posts.setValue(settings.get("max_posts_per_day", 25))
        layout.addRow("Max posts / day", self.spin_max_posts)

        self.spin_metrics = QtWidgets.QSpinBox()
        self.spin_metrics.setRange(5, 120)
        self.spin_metrics.setValue(settings.get("metrics_refresh_minutes", 30))
        layout.addRow("Metrics refresh (min)", self.spin_metrics)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        layout.addRow(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    # --------------------------------------------------------------
    def values(self) -> dict:
        return {
            "max_posts_per_day": self.spin_max_posts.value(),
            "metrics_refresh_minutes": self.spin_metrics.value(),
        }

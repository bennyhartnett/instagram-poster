from datetime import time
import os

import pytest

try:
    from PySide6 import QtWidgets
    from gui.schedule_dialog import ScheduleDialog
except Exception:  # pragma: no cover - missing Qt deps
    QtWidgets = None
    ScheduleDialog = None


@pytest.mark.skipif(ScheduleDialog is None, reason="PySide6 not available")
def test_schedule_dialog_returns_template():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    template = [time(8, 0), time(12, 30)]
    dlg = ScheduleDialog(template)
    assert dlg.schedule_template == template


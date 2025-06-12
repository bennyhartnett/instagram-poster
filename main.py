"""Entry point for the desktop application."""
from PySide6 import QtWidgets

from backend import db, models, watcher, scheduler
from gui.main_window import MainWindow


def main() -> None:
    # Initialize database
    models.Base.metadata.create_all(db.ENGINE)
    session = next(db.get_session())

    # Load settings
    import json
    with open("settings.json", "r") as f:
        settings = json.load(f)
    session.settings = settings

    # Start folder watcher
    if settings.get("watch_folder"):
        observer = watcher.start_watcher(settings["watch_folder"], session)
    else:
        observer = None

    sched = scheduler.create_scheduler(session, settings.get("max_posts_per_day", 25))

    app = QtWidgets.QApplication([])
    win = MainWindow(session, sched)
    win.show()
    app.exec()

    if sched:
        sched.shutdown(wait=False)
    if observer:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()

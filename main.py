"""Entry point for the desktop application."""
from PySide6 import QtWidgets


def _graceful_shutdown(app: QtWidgets.QApplication, sched, observer) -> None:
    """Connect clean-up handlers to the Qt application."""
    def _on_quit():
        if sched:
            sched.shutdown(wait=False)
        if observer:
            observer.stop()
            observer.join()

    app.aboutToQuit.connect(_on_quit)


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
    _graceful_shutdown(app, sched, observer)
    win = MainWindow(session, sched)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()

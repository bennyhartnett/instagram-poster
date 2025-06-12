"""Folder watching and hashing utilities."""
import hashlib
import pathlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .models import Video


class FolderHandler(FileSystemEventHandler):
    """Handle new files appearing in the watch folder."""

    def __init__(self, session):
        super().__init__()
        self.session = session

    def on_created(self, event):
        if event.is_directory:
            return
        path = pathlib.Path(event.src_path)
        if path.suffix.lower() not in {".mp4", ".mov", ".mkv"}:
            return
        sha256 = _hash_file(path)
        if not self.session.query(Video).filter_by(sha256=sha256).first():
            self.session.add(Video(file_path=str(path), sha256=sha256))
            self.session.commit()


def _hash_file(path: pathlib.Path, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(chunk_size), b""):
            h.update(blk)
    return h.hexdigest()


def start_watcher(folder: str, session) -> Observer:
    """Start an Observer thread watching the given folder."""
    handler = FolderHandler(session)
    obs = Observer()
    obs.schedule(handler, folder, recursive=False)
    obs.daemon = True
    obs.start()
    return obs

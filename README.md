# instagram-poster

This repository contains an outline for a desktop application that schedules and uploads videos to Instagram via the Graph API.

## Quick Start

1. Create a Python 3.11+ virtual environment.
2. Install dependencies from `requirements.txt`:

   ```bash
   pip install -r requirements.txt
   ```

3. Edit `settings.json` to configure your watch folder and Instagram credentials.
4. Run the app with:

   ```bash
   python main.py
   ```

The GUI opens and begins watching the configured folder for new videos.

## Running Tests

Ensure the dependencies from `requirements.txt` are installed and then run `pytest`:

```bash
pip install -r requirements.txt
pytest
```

## Technology Stack

| Layer                     | Package / Framework             | Purpose                                                                                   |
|---------------------------|---------------------------------|-------------------------------------------------------------------------------------------|
| Desktop GUI               | PySide 6 (Qt for Python)        | Native look and feel on Windows/macOS/Linux; rich widgets such as trees and media player. |
| ORM & DB                  | SQLAlchemy 2 + SQLite           | Single file DB (`project.db`) with autocommits and migrations via Alembic.                |
| Video playback & thumbnails | PySide6.QtMultimedia + ffmpeg-python | Playback and thumbnail generation.                                                        |
| File Watch / Hashing      | watchdog + `hashlib.sha256`     | Detect new videos and avoid duplicates.                                                   |
| Task Scheduler            | APScheduler (background thread) | Cron/interval/date jobs; persists next-run times so jobs survive restarts.               |
| Instagram client          | `requests` + small helper       | Wrapper around the Graph API.                                                             |
| Secrets storage           | `keyring`                       | Stores the long-lived user token securely.                                                |

## Data Model

```python
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, create_engine
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    sha256 = Column(String, unique=True, nullable=False)
    title = Column(String, default="")
    description = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime)  # null → unscheduled
    posted_at = Column(DateTime)
    insta_media_id = Column(String)  # returned after publish
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    last_error = Column(String)
    is_active = Column(Boolean, default=True)  # soft-delete
```

Unschedule a video by setting `scheduled_at` to `None`. The record remains for duplicate detection.

## Folder Watcher & Hashing

```python
import hashlib
import pathlib
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FolderHandler(FileSystemEventHandler):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def on_created(self, evt):
        if evt.is_directory:  # ignore sub-dirs
            return
        path = pathlib.Path(evt.src_path)
        if path.suffix.lower() not in {".mp4", ".mov", ".mkv"}:
            return
        sha256 = _hash_file(path)
        if not session.query(Video).filter_by(sha256=sha256).first():
            session.add(Video(file_path=str(path), sha256=sha256))
            session.commit()

def _hash_file(path: pathlib.Path, chunk=8192) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()
```

Run the observer in a daemon thread so the GUI stays responsive.

## Scheduler Logic (APScheduler)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


def post_due_videos():
    now = datetime.utcnow()
    videos = (
        session.query(Video)
        .filter(Video.scheduled_at <= now, Video.posted_at.is_(None))
        .order_by(Video.scheduled_at)
        .all()
    )
    todays_count = (
        session.query(Video)
        .filter(func.date(Video.posted_at) == date.today())
        .count()
    )
    allowance = max_posts_per_day - todays_count
    for vid in videos[:allowance]:
        try:
            post_to_instagram(vid)
            vid.posted_at = datetime.utcnow()
            session.commit()
        except Exception as exc:
            vid.last_error = str(exc)
            session.commit()


sched = BackgroundScheduler(daemon=True)
sched.add_job(post_due_videos, "interval", minutes=1)
sched.start()
```

`max_posts_per_day` is stored in settings (default 25). Changing the value takes effect without a restart.

## Posting to the Instagram Graph API

```python
import requests
import time

API = "https://graph.facebook.com/v21.0"


def post_to_instagram(video: Video):
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    user_id = SETTINGS.INSTAGRAM_USER_ID  # stored once in settings form

    # 1. Create container
    r = requests.post(
        f"{API}/{user_id}/media",
        data={
            "video_url": _local_http_url(video.file_path),
            "caption": f"{video.title}\n\n{video.description}",
            "published": "false",
        },
        params={"access_token": token},
        timeout=300,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    # 2. Poll container status (IG takes minutes for videos)
    while True:
        status = requests.get(
            f"{API}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        ).json()["status_code"]
        if status == "FINISHED":
            break
        elif status == "ERROR":
            raise RuntimeError("IG processing failed")
        time.sleep(10)

    # 3. Publish
    r = requests.post(
        f"{API}/{user_id}/media_publish",
        data={"creation_id": container_id},
        params={"access_token": token},
    )
    r.raise_for_status()
    video.insta_media_id = r.json()["id"]
```

Local hosting trick: run a minimal HTTP server bound to localhost and post a `video_url` like `http://127.0.0.1:8080/tmp/<sha>.mp4`. In production you would likely upload to S3 or another publicly accessible location.

## Metrics Refresh Task

```python
def refresh_metrics():
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    vids = session.query(Video).filter(Video.insta_media_id.isnot(None)).all()
    for v in vids:
        r = requests.get(
            f"{API}/{v.insta_media_id}",
            params={
                "fields": "like_count,comments_count,video_view_count",
                "access_token": token,
            },
        ).json()
        v.likes = r.get("like_count", 0)
        v.comments = r.get("comments_count", 0)
        v.views = r.get("video_view_count", 0)
    session.commit()


sched.add_job(refresh_metrics, "interval", minutes=30)
```

## GUI (PySide 6)

### Main Window Layout

* Left pane – folder tree and filters
* Right pane – accordion list (`QTreeWidget`)

Each accordion item (top-level `QTreeWidgetItem`) contains:

| Widget | Purpose |
| --- | --- |
| Thumbnail (`QLabel`) | Preview generated with `ffmpeg -ss 00:00:01 -vframes 1` |
| Title (`QLineEdit`) | Editable; saved on focus out |
| Schedule (`QDateTimeEdit`) | Allows setting or clearing schedule |
| Status chip (`QLabel`) | Shows `Unscheduled`, `Scheduled`, `Posted`, or `Error` |
| Play button | Opens a modal dialog with `QMediaPlayer` |
| Metrics (`QFormLayout`) | Likes / comments / views (read-only but refreshable) |
| Delete & Post‑Now buttons | Hard delete (moves file to Recycle Bin) or immediate posting |

Qt’s `QTreeWidget` gives collapsible rows for free—each top-level item can be expanded to reveal a custom child widget with the detail form.

### Schedule Grid Dialog

A `QDialog` with a `QTableWidget`:

```
Row | Column 1 (active) | Column 2 (time)
1   | [checkbox]        | QTimeEdit (default 08:00)
... | ...               | ...
```

Up to 25 rows. On Save, active rows are converted into a per‑day template. The background scheduler uses that template plus the selected date to set `scheduled_at` for newly added videos.

## Configuration Panel

| Setting | Widget | Notes |
| --- | --- | --- |
| Instagram User ID | `QLineEdit` | Numeric string |
| Long‑lived Token | `QLineEdit` | Stored via `keyring` on Apply |
| Max posts / day | `QSpinBox` (0–25) | Immediate effect |
| Metrics refresh minutes | `QSpinBox` | 5–120 |
| Time‑zone override | `QComboBox` (pytz) | Only necessary if system TZ differs from desired posting TZ |

## Packaging & Install

1. Create a virtual environment using Python 3.11+ and install dependencies:

   ```bash
   pip install pyside6 sqlalchemy apscheduler watchdog ffmpeg-python requests keyring pytz alembic
   ```

2. Ensure the FFmpeg binary is on `PATH` (on Windows bundle `ffmpeg.exe` in `./bin`).

3. Run the provided build script to create a single-file executable:

   ```bash
   python build.py
   ```

   The script invokes `PyInstaller` with the appropriate options (see
   `build.py` for the exact command).

Ship the resulting executable together with a small README describing the Instagram permission steps.

## Putting It All Together

```
main.py
│
├─ gui/
│   ├─ main_window.py
│   ├─ schedule_dialog.py
│   └─ widgets.py
│
├─ backend/
│   ├─ db.py           # engine & session
│   ├─ models.py       # Video class
│   ├─ watcher.py      # folder observer
│   ├─ scheduler.py    # APScheduler configuration
│   └─ instagram.py    # API wrapper
│
└─ settings.json       # non-secret prefs (folder path, refresh minutes, max/day)
```

Running `python main.py`:

1. Spins up the SQLite DB (migrates if first run).
2. Starts the folder watcher.
3. Loads the APScheduler jobs (posting & metrics).
4. Presents the PySide 6 window.

Everything persists in local files; the only network calls are to Instagram when posting or refreshing stats.

### Next Steps

* Install permissions – ensure your Facebook App is in Live mode and the token includes `instagram_content_publish`.
* Unit tests – create pytest fixtures for hashing, DB operations and mock the Graph API calls with responses.
* Graceful shutdown – trap `QApplication.aboutToQuit` → `sched.shutdown(wait=False)` → `observer.stop()`.

With this all Python plan you get a native desktop scheduler, zero external servers and clear boundaries between GUI, persistence and the posting engine.

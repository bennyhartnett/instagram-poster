# instagram-poster

1. Technology Stack (all Python)
Layer	Package / Framework	Purpose
Desktop GUI	PySide 6 (Qt for Python)	Native look‑and‑feel on Windows/macOS/Linux, rich widgets (tree/accordion, date‑time pickers, media player).
ORM & DB	SQLAlchemy 2 + SQLite	Single‐file DB (project.db), autocommits, migrations via alembic.
Video Playback & Thumbnails	PySide6.QtMultimedia for playback; ffmpeg‑python to grab thumbnails.	
File Watch / Hashing	watchdog + hashlib.sha256.	
Task Scheduler	APScheduler (background thread) – supports cron/interval/date jobs; survives GUI restarts by persisting next‑run times in DB.	
Instagram Client	requests + small helper wrapping the Graph API.	
Secrets Storage	keyring (platform keychain) – stores long‑lived user token securely.	

2. Data Model (SQLAlchemy ORM)
python
Copy
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, create_engine
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"

    id                = Column(Integer, primary_key=True)
    file_path         = Column(String, unique=True, nullable=False)
    sha256            = Column(String, unique=True, nullable=False)
    title             = Column(String, default="")
    description       = Column(String, default="")
    created_at        = Column(DateTime, default=datetime.utcnow)
    scheduled_at      = Column(DateTime)      # null → unscheduled
    posted_at         = Column(DateTime)
    insta_media_id    = Column(String)        # returned after publish
    likes             = Column(Integer, default=0)
    comments          = Column(Integer, default=0)
    views             = Column(Integer, default=0)
    last_error        = Column(String)
    is_active         = Column(Boolean, default=True)  # soft‑delete
Unschedule by setting scheduled_at = None; the record stays for hash‑duplicate detection.

3. Folder Watcher & Hashing
python
Copy
import hashlib, pathlib, time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FolderHandler(FileSystemEventHandler):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def on_created(self, evt):
        if evt.is_directory:  # ignore sub‑dirs
            return
        path = pathlib.Path(evt.src_path)
        if path.suffix.lower() not in {".mp4", ".mov", ".mkv"}:  # extend as needed
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
Run the observer in a daemon thread so the GUI stays responsive.

4. Scheduler Logic (APScheduler)
python
Copy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

def post_due_videos():
    now = datetime.utcnow()
    videos = (session.query(Video)
                     .filter(Video.scheduled_at <= now,
                             Video.posted_at.is_(None))
                     .order_by(Video.scheduled_at)
                     .all())
    # Enforce per‑day cap
    todays_count = (session.query(Video)
                           .filter(func.date(Video.posted_at) == date.today())
                           .count())
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
max_posts_per_day is a global integer stored in a settings table or JSON file (default 25). When the user changes it, update the value; no restart necessary.

5. Posting to Instagram Graph API
python
Copy
import requests, time

API = "https://graph.facebook.com/v21.0"

def post_to_instagram(video: Video):
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    user_id = SETTINGS.INSTAGRAM_USER_ID  # stored once in settings form
    # 1. Create container
    r = requests.post(
        f"{API}/{user_id}/media",
        data={
            "video_url": _local_http_url(video.file_path),  # see note below
            "caption": f"{video.title}\n\n{video.description}",
            "published": "false"
        },
        params={"access_token": token},
        timeout=300
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    # 2. Poll container status (IG takes minutes for videos)
    while True:
        status = requests.get(
            f"{API}/{container_id}",
            params={"fields": "status_code", "access_token": token}
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
        params={"access_token": token}
    )
    r.raise_for_status()
    video.insta_media_id = r.json()["id"]
Local hosting trick: spin up a minimal HTTP server (e.g., aiohttp.web) bound to localhost and POST a video_url like http://127.0.0.1:8080/tmp/<sha>.mp4. Instagram’s crawler must reach it, so during real runs you’ll likely push to S3 or a throw‑away DigitalOcean Space instead. Swap _local_http_url with an S3 presigned link generator if preferred.

6. Metrics Refresh Task
python
Copy
def refresh_metrics():
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    vids = session.query(Video).filter(Video.insta_media_id.isnot(None)).all()
    for v in vids:
        r = requests.get(
            f"{API}/{v.insta_media_id}",
            params={"fields": "like_count,comments_count,video_view_count",
                    "access_token": token}
        ).json()
        v.likes    = r.get("like_count", 0)
        v.comments = r.get("comments_count", 0)
        v.views    = r.get("video_view_count", 0)
    session.commit()

sched.add_job(refresh_metrics, "interval", minutes=30)
7. GUI (PySide 6)
7.1 Main Window Layout
Left pane – Folder tree & filters

Right pane – Accordion list (QTreeWidget)

Each accordion item (top‑level QTreeWidgetItem) contains:

Widget	Purpose
Thumbnail (QLabel)	Static preview generated with ffmpeg -ss 00:00:01 -vframes 1.
Title (QLineEdit)	Editable; saved on focus‑out.
Schedule (QDateTimeEdit)	Allows setting / clearing schedule.
Status chip (QLabel with style sheet)	Shows Unscheduled, Scheduled, Posted, Error.
Play Button	Launches a modal dialog with QMediaPlayer inside.
Metrics (QFormLayout)	Likes / Comments / Views (read‑only but refreshable).
Delete & Post‑Now buttons	Hard delete (moves file to Recycle Bin) or immediate posting.

Qt’s QTreeWidget gives you collapsible rows (accordion effect) for free—each top‑level item can be expanded to reveal a custom child widget containing the detail form.

7.2 Schedule Grid Dialog
QDialog with a QTableWidget:

Row	Column 1	Column 2
1	Checkbox (active)	QTimeEdit (default 08:00)
…	…	…

Up to 25 rows. On “Save”, convert active time rows into a per‑day template; the background scheduler then uses that template + selected date to set scheduled_at for newly added videos.

8. Configuration Panel
Setting	Widget	Notes
Instagram User ID	QLineEdit	Numeric string.
Long‑lived Token	QLineEdit (PasswordEchoOnEdit)	Stored via keyring on Apply.
Max posts / day	QSpinBox (0–25)	Immediate effect.
Metrics refresh minutes	QSpinBox	5–120.
Time‑zone override	QComboBox (pytz)	Only necessary if system TZ ≠ desired posting TZ.

9. Packaging & Install
Create a virtualenv with Python 3.11 +

pip install pyside6 sqlalchemy apscheduler watchdog ffmpeg-python requests keyring pytz alembic

Ensure FFmpeg binary is on PATH (Windows: bundle ffmpeg.exe in ./bin).

Use PyInstaller to build a single‑folder distribution:

bash
Copy
pyinstaller -n IGScheduler \
            --add-binary="bin/ffmpeg.exe;bin" \
            --exclude-module=tkinter \
            --onefile main.py
Ship the resulting executable and a README.md with the Instagram permission steps.

10. Putting It All Together
text
Copy
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
└─ settings.json       # non‑secret prefs (folder path, refresh minutes, max/day)
Running python main.py:

Spins up the SQLite DB (migrate if first run).

Starts the folder watcher.

Loads the APScheduler jobs (posting & metrics).

Presents the PySide 6 window.

Everything persists in local files; the only network calls are to Instagram when posting or refreshing stats.

Next Steps
Install permissions – make sure your Facebook App is in Live mode and the account token contains instagram_content_publish.

Unit tests – create pytest fixtures for hashing, DB ops, and mock the Graph API calls with responses.

Graceful shutdown – trap QApplication.aboutToQuit ⇒ sched.shutdown(wait=False) ⇒ observer.stop().

With this all‑Python plan you get a native desktop scheduler, zero external servers, and clear boundaries between GUI, persistence, and the posting engine. Let me know if you need code for a specific module, help wiring the PySide accordion, or guidance on packaging the FFmpeg runtime!








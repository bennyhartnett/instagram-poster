"""Minimal Instagram Graph API helper."""
from __future__ import annotations

import functools
import hashlib
import http.server
import shutil
import socketserver
import tempfile
import threading
import time
from pathlib import Path

import keyring
import requests

from .models import Video

API = "https://graph.facebook.com/v21.0"

# ---------------------------------------------------------------------------
# Local HTTP server to expose files to the Instagram API
# ---------------------------------------------------------------------------
SERVE_DIR = Path(tempfile.gettempdir()) / "ig_uploads"
_SERVER: socketserver.TCPServer | None = None
_THREAD: threading.Thread | None = None
_PORT: int | None = None


def start_http_server(port: int = 0) -> int:
    """Start a background HTTP server serving ``SERVE_DIR``."""
    global _SERVER, _THREAD, _PORT
    if _SERVER:
        return _PORT or 0

    SERVE_DIR.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SERVE_DIR))
    _SERVER = socketserver.TCPServer(("127.0.0.1", port), handler)
    _PORT = _SERVER.server_address[1]
    _THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True)
    _THREAD.start()
    return _PORT


def stop_http_server() -> None:
    """Stop the background HTTP server if running."""
    global _SERVER, _THREAD, _PORT
    if _SERVER:
        _SERVER.shutdown()
        _SERVER.server_close()
        _SERVER = None
        _THREAD = None
        _PORT = None


def _local_http_url(file_path: str) -> str:
    """Copy ``file_path`` to ``SERVE_DIR`` and return an accessible URL."""
    port = start_http_server()

    src = Path(file_path)
    with src.open("rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    dest = SERVE_DIR / f"{sha}{src.suffix}"
    if not dest.exists():
        shutil.copy2(src, dest)

    return f"http://127.0.0.1:{port}/{dest.name}"


def post_to_instagram(session, video):
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    user_id = session.settings.get("instagram_user_id", "")
    if not token or not user_id:
        raise RuntimeError("Instagram credentials not configured")

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

    r = requests.post(
        f"{API}/{user_id}/media_publish",
        data={"creation_id": container_id},
        params={"access_token": token},
    )
    r.raise_for_status()
    video.insta_media_id = r.json()["id"]


def refresh_metrics(session):
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    vids = session.query(Video).filter(Video.insta_media_id.isnot(None)).all()
    for v in vids:
        r = requests.get(
            f"{API}/{v.insta_media_id}",
            params={"fields": "like_count,comments_count,video_view_count", "access_token": token},
        ).json()
        v.likes = r.get("like_count", 0)
        v.comments = r.get("comments_count", 0)
        v.views = r.get("video_view_count", 0)
    session.commit()

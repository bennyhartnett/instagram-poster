import urllib.request
from backend import instagram


def test_local_http_url(tmp_path):
    file_path = tmp_path / "vid.mp4"
    data = b"hello"
    file_path.write_bytes(data)

    url = instagram._local_http_url(str(file_path))
    with urllib.request.urlopen(url) as resp:
        assert resp.read() == data

    instagram.stop_http_server()

import json
from types import SimpleNamespace

from backend.models import Base, Video
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_post_to_instagram(monkeypatch):
    session = create_session()
    vid = Video(file_path="a.mp4", sha256="x")
    session.add(vid)
    session.commit()
    session.settings = {"instagram_user_id": "1"}

    # Fake credentials
    monkeypatch.setattr(instagram.keyring, "get_password", lambda *a, **k: "token")

    def fake_local(url):
        return "http://local/file.mp4"

    monkeypatch.setattr(instagram, "_local_http_url", fake_local)

    posts = []
    gets = []

    def fake_post(url, data=None, params=None, timeout=None):
        posts.append((url, data, params))
        if "media_publish" in url:
            return SimpleNamespace(json=lambda: {"id": "media123"}, raise_for_status=lambda: None)
        else:
            return SimpleNamespace(json=lambda: {"id": "container1"}, raise_for_status=lambda: None)

    def fake_get(url, params=None):
        gets.append((url, params))
        return SimpleNamespace(json=lambda: {"status_code": "FINISHED"})

    monkeypatch.setattr(instagram.requests, "post", fake_post)
    monkeypatch.setattr(instagram.requests, "get", fake_get)
    monkeypatch.setattr(instagram.time, "sleep", lambda s: None)

    instagram.post_to_instagram(session, vid)
    assert vid.insta_media_id == "media123"
    assert any("media_publish" in c[0] for c in posts)


def test_refresh_metrics(monkeypatch):
    session = create_session()
    vid = Video(file_path="a.mp4", sha256="x", insta_media_id="123")
    session.add(vid)
    session.commit()
    session.settings = {"instagram_user_id": "1"}

    monkeypatch.setattr(instagram.keyring, "get_password", lambda *a, **k: "token")

    def fake_get(url, params=None):
        return SimpleNamespace(json=lambda: {"like_count": 1, "comments_count": 2, "video_view_count": 3})

    monkeypatch.setattr(instagram.requests, "get", fake_get)

    instagram.refresh_metrics(session)
    updated = session.get(Video, vid.id)
    assert updated.likes == 1 and updated.comments == 2 and updated.views == 3

from types import SimpleNamespace

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, Video
from backend import instagram
import keyring
import requests


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_post_to_instagram(monkeypatch):
    session = create_session()
    session.settings = {"instagram_user_id": "123"}
    vid = Video(file_path="foo.mp4", sha256="h")
    session.add(vid)
    session.commit()

    # Mock keyring and requests
    monkeypatch.setattr(keyring, "get_password", lambda *_: "tok")

    posts = []

    def fake_post(url, data=None, params=None, timeout=None):
        posts.append(url)
        if url.endswith("/media"):
            return SimpleNamespace(json=lambda: {"id": "cont"}, raise_for_status=lambda: None)
        else:
            return SimpleNamespace(json=lambda: {"id": "pub"}, raise_for_status=lambda: None)

    def fake_get(url, params=None):
        return SimpleNamespace(json=lambda: {"status_code": "FINISHED"})

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)

    instagram.post_to_instagram(session, vid)

    assert vid.insta_media_id == "pub"
    assert posts[0].endswith("/media")
    assert posts[1].endswith("/media_publish")


def test_refresh_metrics(monkeypatch):
    session = create_session()
    monkeypatch.setattr(keyring, "get_password", lambda *_: "tok")
    vid = Video(file_path="f.mp4", sha256="a", insta_media_id="42")
    session.add(vid)
    session.commit()

    def fake_get(url, params=None):
        return SimpleNamespace(json=lambda: {"like_count": 1, "comments_count": 2, "video_view_count": 3})

    monkeypatch.setattr(requests, "get", fake_get)

    instagram.refresh_metrics(session)

    assert vid.likes == 1
    assert vid.comments == 2
    assert vid.views == 3

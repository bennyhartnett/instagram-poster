"""Minimal Instagram Graph API helper."""
import time
import requests
import keyring
from .models import Video

API = "https://graph.facebook.com/v21.0"


def post_to_instagram(session, video):
    token = keyring.get_password("ig_scheduler", "long_lived_token")
    user_id = session.settings.get("instagram_user_id", "")
    if not token or not user_id:
        raise RuntimeError("Instagram credentials not configured")

    r = requests.post(
        f"{API}/{user_id}/media",
        data={
            "video_url": video.file_path,
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

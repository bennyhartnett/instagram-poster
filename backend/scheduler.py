"""Background scheduler configuration."""
from datetime import datetime, date, time, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Video
from .utils import get_timezone
from .instagram import post_to_instagram, refresh_metrics


def post_due_videos(session: Session, max_posts_per_day: int):
    tz = get_timezone(getattr(session, "settings", None))
    now = datetime.utcnow()
    videos = (
        session.query(Video)
        .filter(Video.scheduled_at <= now, Video.posted_at.is_(None))
        .order_by(Video.scheduled_at)
        .all()
    )

    today = datetime.now(tz).date()
    start_local = datetime.combine(today, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    todays_count = (
        session.query(Video)
        .filter(Video.posted_at >= start_utc, Video.posted_at < end_utc)
        .count()
    )
    allowance = max_posts_per_day - todays_count
    for vid in videos[:allowance]:
        try:
            post_to_instagram(session, vid)
            vid.posted_at = datetime.utcnow()
            session.commit()
        except Exception as exc:  # pragma: no cover - network errors
            vid.last_error = str(exc)
            session.commit()


def create_scheduler(session: Session, max_posts_per_day: int) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(post_due_videos, "interval", minutes=1, args=[session, max_posts_per_day])
    scheduler.add_job(refresh_metrics, "interval", minutes=30, args=[session])
    scheduler.start()
    return scheduler

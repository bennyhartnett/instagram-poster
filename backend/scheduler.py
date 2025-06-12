"""Background scheduler configuration."""
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from sqlalchemy import func

from .models import Video
from .instagram import post_to_instagram, refresh_metrics


def post_due_videos(session: Session, max_posts_per_day: int):
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
            post_to_instagram(session, vid)
            vid.posted_at = datetime.utcnow()
            session.commit()
        except Exception as exc:  # pragma: no cover - network errors
            vid.last_error = str(exc)
            session.commit()


def create_scheduler(
    session: Session,
    max_posts_per_day: int,
    metrics_refresh_minutes: int = 30,
) -> BackgroundScheduler:
    """Create and start the background scheduler."""
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        post_due_videos,
        "interval",
        minutes=1,
        args=[session, max_posts_per_day],
    )
    scheduler.add_job(
        refresh_metrics,
        "interval",
        minutes=metrics_refresh_minutes,
        args=[session],
    )
    scheduler.start()
    return scheduler

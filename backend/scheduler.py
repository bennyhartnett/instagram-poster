"""Background scheduler configuration."""
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
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


def create_scheduler(session: Session, max_posts_per_day: int) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        post_due_videos,
        "interval",
        minutes=1,
        args=[session, max_posts_per_day],
        id="post_due_videos",
    )
    scheduler.add_job(
        refresh_metrics,
        "interval",
        minutes=30,
        args=[session],
        id="refresh_metrics",
    )
    scheduler.start()
    return scheduler


def update_post_job(scheduler: BackgroundScheduler, max_posts_per_day: int) -> None:
    """Modify the post job arguments when settings change."""
    job = scheduler.get_job("post_due_videos")
    if job:
        args = list(job.args)
        if len(args) >= 2:
            args[1] = max_posts_per_day
        else:
            args.append(max_posts_per_day)
        scheduler.modify_job(job.id, args=args)


def update_metrics_job(scheduler: BackgroundScheduler, minutes: int) -> None:
    """Reschedule the metrics refresh job with a new interval."""
    job = scheduler.get_job("refresh_metrics")
    if job:
        scheduler.reschedule_job(job.id, trigger=IntervalTrigger(minutes=minutes))

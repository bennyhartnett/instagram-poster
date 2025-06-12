from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import scheduler
from backend.models import Base, Video


def create_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_post_due_videos(monkeypatch):
    session = create_session()
    now = datetime.utcnow() - timedelta(hours=1)

    v1 = Video(file_path="1.mp4", sha256="a", scheduled_at=now)
    v2 = Video(file_path="2.mp4", sha256="b", scheduled_at=now + timedelta(minutes=1))
    session.add_all([v1, v2])
    session.commit()

    posted = []

    def fake_post(session_arg, video):
        posted.append(video)

    monkeypatch.setattr(scheduler, "post_to_instagram", fake_post)
    scheduler.post_due_videos(session, max_posts_per_day=1)

    assert len(posted) == 1
    assert v1.posted_at is not None
    assert v2.posted_at is None


def test_create_scheduler_uses_refresh_interval():
    session = create_session()
    sched = scheduler.create_scheduler(session, 1, metrics_refresh_minutes=42)
    # Find the refresh_metrics job
    job = next(j for j in sched.get_jobs() if j.func == scheduler.refresh_metrics)
    assert job.trigger.interval.total_seconds() == 42 * 60
    sched.shutdown(wait=False)

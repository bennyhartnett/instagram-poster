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


def test_update_jobs():
    session = create_session()
    sched = scheduler.create_scheduler(session, max_posts_per_day=5)
    # update post job
    scheduler.update_post_job(sched, 10)
    post_job = sched.get_job("post_due_videos")
    assert post_job.args[1] == 10

    # update metrics interval
    scheduler.update_metrics_job(sched, 15)
    metrics_job = sched.get_job("refresh_metrics")
    assert metrics_job.trigger.interval.seconds == 15 * 60

    sched.shutdown()

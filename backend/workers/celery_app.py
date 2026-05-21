from celery import Celery

from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "shopping_avatar",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.task_track_started = True
celery_app.conf.result_expires = 3600


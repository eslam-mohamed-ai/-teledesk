from celery import Celery
from celery.signals import setup_logging

from app.config import settings
from app.logging_config import configure_logging


@setup_logging.connect
def configure_celery_logging(**kwargs):
    configure_logging()


celery = Celery("teledesk", broker=settings.REDIS_URL, backend=settings.REDIS_URL,
                include=["app.workers.process_document", "app.workers.handle_message"])
celery.conf.task_track_started = True

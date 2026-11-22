from celery import Celery
from celery.signals import setup_logging
from kombu import Queue

from app.config import settings
from app.logging_config import configure_logging


@setup_logging.connect
def configure_celery_logging(**kwargs):
    configure_logging()


celery = Celery(
    "teledesk",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.process_document",
        "app.workers.handle_message",
        "app.pipeline.turn",
        "app.pipeline.outbound",
    ],
)

celery.conf.task_track_started = True
celery.conf.task_acks_late = True
celery.conf.task_reject_on_worker_lost = True
celery.conf.task_acks_on_failure_or_timeout = False
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_time_limit = 300
celery.conf.task_soft_time_limit = 270
celery.conf.broker_transport_options = {
    "visibility_timeout": 3600,
    "max_retries": 10,
    "interval_start": 0,
    "interval_step": 0.5,
    "interval_max": 5,
}

celery.conf.task_routes = {
    "app.pipeline.outbound.send_outbound": {"queue": "outbound"},
    "app.pipeline.turn.process_conversation_turn": {"queue": "turns"},
}

celery.conf.task_default_queue = "default"
celery.conf.task_queues = (
    Queue("default"),
    Queue("turns"),
    Queue("outbound"),
)

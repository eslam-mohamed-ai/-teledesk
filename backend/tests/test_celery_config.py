"""Celery configuration verification.

Verifies queue routing, time limits, ack/reject semantics, and prefetch
settings. Runs without a database (imports app.workers.celery_app only).
"""

from app.workers.celery_app import celery


def test_celery_broker_and_backend_use_redis():
    assert str(celery.conf.broker_url).startswith("redis://")
    assert str(celery.conf.result_backend).startswith("redis://")


def test_celery_queues_defined():
    queue_names = {q.name for q in celery.conf.task_queues}
    assert {"default", "turns", "outbound"} <= queue_names


def test_celery_task_routes():
    routes = celery.conf.task_routes
    assert routes["app.pipeline.outbound.send_outbound"]["queue"] == "outbound"
    assert routes["app.pipeline.turn.process_conversation_turn"]["queue"] == "turns"


def test_celery_acks_and_reject_semantics():
    assert celery.conf.task_acks_late is True
    assert celery.conf.task_reject_on_worker_lost is True
    assert celery.conf.task_acks_on_failure_or_timeout is False


def test_celery_prefetch_and_time_limits():
    assert celery.conf.worker_prefetch_multiplier == 1
    assert celery.conf.task_time_limit == 300
    assert celery.conf.task_soft_time_limit == 270


def test_celery_task_track_started():
    assert celery.conf.task_track_started is True

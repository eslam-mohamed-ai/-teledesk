import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.services import storage


router = APIRouter(tags=["health"])
log = logging.getLogger("teledesk.health")


def _check_database() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def _check_redis() -> None:
    client = Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        client.ping()
    finally:
        client.close()


def _check_storage() -> None:
    storage.check_bucket()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/readyz")
def readyz():
    checks = {
        "database": _check_database,
        "redis": _check_redis,
        "storage": _check_storage,
    }
    results = {}

    for name, check in checks.items():
        try:
            check()
            results[name] = "ok"
        except Exception:
            log.exception("Readiness check failed: dependency=%s", name)
            results[name] = "unavailable"

    status = "ready" if all(value == "ok" for value in results.values()) else "not_ready"
    response_status = 200 if status == "ready" else 503
    return JSONResponse(
        status_code=response_status,
        content={"status": status, "checks": results},
    )

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import FRONTEND_DIR
from app.static import SPAFiles
from app.database import init_db
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes import (
    auth,
    billing,
    bots,
    channels,
    company,
    conversations,
    contacts,
    documents,
    health,
    onboarding,
    realtime,
    stats,
    team,
    webhooks,
)
from app.services import storage

configure_logging()

log = logging.getLogger("teledesk")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("Initializing database...")
    init_db()

    log.info("Checking MinIO storage...")
    storage.ensure_bucket()

    log.info("TeleDesk startup completed.")
    yield


app = FastAPI(title="TeleDesk", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)

for r in (auth, company, documents, bots, conversations, contacts, stats, billing, team, onboarding, realtime):
    app.include_router(r.router, prefix="/api")

app.include_router(webhooks.router)
app.include_router(channels.router)
app.include_router(channels.webhook_router)
app.include_router(health.router)

# الواجهة تتخدم من نفس السيرفر (لازم تتحط آخر حاجة)
# SPA fallback: unknown non-API paths return index.html so client-side routes
# like /inbox survive a hard refresh. Skipped when no build is present
# (e.g. backend-only test runs).
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", SPAFiles(directory=FRONTEND_DIR, html=True), name="frontend")
"""Company-scoped realtime SSE endpoint.

Clients connect to GET /api/realtime and receive server-sent events for
their own company only. The Redis channel is keyed by company_id so tenants
can never see each other's events.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.deps import current_company, current_user
from app.models import Company, User
from app.pipeline.realtime import Subscriber

router = APIRouter(prefix="/realtime", tags=["realtime"])
log = logging.getLogger("teledesk.realtime")


@router.get("")
async def realtime_events(
    request: Request,
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
):
    """SSE stream of realtime events for the current user's company.

    Only events published to ``teledesk:realtime:company:{c.id}`` are sent,
    so company A can never receive company B's events.
    """
    subscriber = Subscriber(c.id)
    await subscriber.connect()

    async def event_iterator() -> Any:
        try:
            async for event in subscriber:
                if await request.is_disconnected():
                    break
                yield f"data: {event}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await subscriber.close()

    return StreamingResponse(
        event_iterator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

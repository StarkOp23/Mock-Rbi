"""Helper to write audit events without boilerplate."""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


async def log_event(
    db: AsyncSession,
    *,
    actor: str,
    event_type: str,
    outcome: str = "success",
    resource_type: str | None = None,
    resource_id:   str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(AuditEvent(
        actor=actor,
        event_type=event_type,
        outcome=outcome,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail or {},
    ))
    # Flush so the row gets an ID inside the same transaction; commit is owned
    # by the request-level get_db() dependency.
    await db.flush()

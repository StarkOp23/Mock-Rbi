"""Audit log endpoints — read-only browsable ledger."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db.session import get_db
from app.db.models import AuditEvent
from app.schemas import AuditEventRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventRead])
async def list_audit_events(
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
    event_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    limit: int = Query(100, le=500),
) -> list[AuditEventRead]:
    stmt = select(AuditEvent).order_by(AuditEvent.id.desc())
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if resource_id:
        stmt = stmt.where(AuditEvent.resource_id == resource_id)
    stmt = stmt.limit(limit)

    rows = (await db.execute(stmt)).scalars().all()
    return [AuditEventRead.model_validate(r) for r in rows]

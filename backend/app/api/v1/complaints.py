"""
Complaint endpoints — RBI staff lifecycle.

Routes:
    POST   /api/v1/complaints                  — create new complaint
    GET    /api/v1/complaints                  — list (paginated, filterable)
    GET    /api/v1/complaints/{id}             — full detail incl forwardings + responses
    GET    /api/v1/complaints/by-ref/{ref}     — fetch by reference_no
    GET    /api/v1/dashboard/stats             — KPI tiles
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db.session import get_db
from app.db.models import (
    Complaint, ComplaintStatus, IntentClass, BankResponse,
)
from app.schemas import (
    ComplaintCreate, ComplaintRead, ComplaintListItem, ComplaintDetail,
    ForwardingRead, BankResponseRead, DashboardStats,
)
from app.services.audit_service import log_event

router = APIRouter(prefix="/complaints", tags=["complaints"])


def _next_reference_no(year: int, month: int, seq: int) -> str:
    return f"RBI-CMS-{year:04d}-{month:02d}-{seq:05d}"


@router.post("", response_model=ComplaintRead, status_code=201)
async def create_complaint(
    payload: ComplaintCreate,
    actor:   Annotated[str, Depends(require_api_key)],
    db:      Annotated[AsyncSession, Depends(get_db)],
) -> ComplaintRead:
    now = datetime.now(timezone.utc)

    # Generate next reference_no for the current YYYY-MM
    last_seq = await db.scalar(
        select(func.count(Complaint.id)).where(
            func.extract("year",  Complaint.received_at) == now.year,
            func.extract("month", Complaint.received_at) == now.month,
        )
    )
    reference_no = _next_reference_no(now.year, now.month, (last_seq or 0) + 1)

    c = Complaint(
        reference_no=reference_no,
        received_at=now,
        status=ComplaintStatus.received,
        **payload.model_dump(),
    )
    db.add(c)
    await db.flush()

    await log_event(
        db, actor=actor, event_type="complaint.created",
        resource_type="complaint", resource_id=c.id,
        detail={"reference_no": reference_no, "bank_code": c.bank_code},
    )

    return ComplaintRead.model_validate(c)


@router.get("", response_model=list[ComplaintListItem])
async def list_complaints(
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
    bank_code: str | None = Query(None),
    status:    ComplaintStatus | None = Query(None),
    intent:    IntentClass | None = Query(None),
    skip: int = 0,
    limit: int = Query(50, le=200),
) -> list[ComplaintListItem]:
    stmt = select(Complaint).order_by(Complaint.received_at.desc())
    if bank_code:
        stmt = stmt.where(Complaint.bank_code == bank_code)
    if status:
        stmt = stmt.where(Complaint.status == status)
    if intent:
        stmt = stmt.where(Complaint.intent_class == intent)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [ComplaintListItem.model_validate(r) for r in rows]


@router.get("/{complaint_id}", response_model=ComplaintDetail)
async def get_complaint(
    complaint_id: str,
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> ComplaintDetail:
    c = await db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found.")

    return ComplaintDetail(
        complaint=ComplaintRead.model_validate(c),
        forwardings=[ForwardingRead.model_validate(f) for f in sorted(c.forwardings, key=lambda x: x.forwarded_at)],
        responses=[BankResponseRead.model_validate(r) for r in sorted(c.responses, key=lambda x: x.received_at)],
    )


@router.get("/by-ref/{reference_no}", response_model=ComplaintDetail)
async def get_by_reference(
    reference_no: str,
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> ComplaintDetail:
    c = await db.scalar(select(Complaint).where(Complaint.reference_no == reference_no))
    if not c:
        raise HTTPException(status_code=404, detail=f"Reference {reference_no} not found.")
    return ComplaintDetail(
        complaint=ComplaintRead.model_validate(c),
        forwardings=[ForwardingRead.model_validate(f) for f in sorted(c.forwardings, key=lambda x: x.forwarded_at)],
        responses=[BankResponseRead.model_validate(r) for r in sorted(c.responses, key=lambda x: x.received_at)],
    )


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> DashboardStats:
    total = await db.scalar(select(func.count(Complaint.id))) or 0

    # by_status
    rows = (await db.execute(
        select(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status)
    )).all()
    by_status = {s.value: int(n) for s, n in rows}

    # by_bank
    rows = (await db.execute(
        select(Complaint.bank_code, func.count(Complaint.id)).group_by(Complaint.bank_code)
    )).all()
    by_bank = {b: int(n) for b, n in rows}

    # by_intent
    rows = (await db.execute(
        select(Complaint.intent_class, func.count(Complaint.id)).group_by(Complaint.intent_class)
    )).all()
    by_intent = {i.value: int(n) for i, n in rows}

    open_count = sum(
        n for s, n in by_status.items()
        if s in (ComplaintStatus.received.value,
                 ComplaintStatus.forwarded_to_bank.value)
    )

    avg_tat = await db.scalar(select(func.avg(BankResponse.tat_days)))
    breach_count = await db.scalar(
        select(func.count(BankResponse.id)).where(BankResponse.breached_30_day.is_(True))
    ) or 0

    return DashboardStats(
        total_complaints=total,
        by_status=by_status,
        by_bank=by_bank,
        by_intent=by_intent,
        open_count=open_count,
        avg_tat_days=float(avg_tat) if avg_tat is not None else None,
        breach_count=int(breach_count),
    )

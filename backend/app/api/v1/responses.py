"""
Bank responses — bank's Crest agent ends with a POST back to RBI.

When the bank-side workflow completes (Node 13/14 — customer letter sent;
Node 15 — RBS register written), the agent makes a closing call to the RBI
mock to inform that the case is resolved. RBI's CMS marks the complaint as
bank_responded and shows the resolution to RBI staff.
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db.session import get_db
from app.db.models import Complaint, ComplaintStatus, BankResponse
from app.schemas import BankResponseCreate, BankResponseRead
from app.services.audit_service import log_event

router = APIRouter(prefix="/responses", tags=["responses"])


@router.post("", response_model=BankResponseRead, status_code=201)
async def post_bank_response(
    payload: BankResponseCreate,
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> BankResponseRead:
    c = await db.scalar(
        select(Complaint).where(Complaint.reference_no == payload.complaint_reference_no)
    )
    if not c:
        raise HTTPException(
            status_code=404,
            detail=f"No complaint with reference {payload.complaint_reference_no}.",
        )

    r = BankResponse(
        complaint_id=c.id,
        bank_code=payload.bank_code,
        outcome=payload.outcome,
        compensation_inr=payload.compensation_inr,
        tat_days=payload.tat_days,
        breached_30_day=payload.breached_30_day,
        customer_letter=payload.customer_letter,
        cited_clauses=payload.cited_clauses,
        bank_run_id=payload.bank_run_id,
        raw_payload=payload.model_dump(),
    )
    db.add(r)

    # Move complaint into bank_responded
    c.status    = ComplaintStatus.bank_responded
    c.closed_at = datetime.now(timezone.utc)

    await log_event(
        db, actor=actor, event_type="bank.response_received",
        resource_type="complaint",
        resource_id=c.id,
        detail={
            "reference_no":     c.reference_no,
            "bank_code":        payload.bank_code,
            "outcome":          payload.outcome.value,
            "compensation_inr": payload.compensation_inr,
            "tat_days":         payload.tat_days,
            "breached_30_day":  payload.breached_30_day,
        },
    )

    await db.flush()
    return BankResponseRead.model_validate(r)

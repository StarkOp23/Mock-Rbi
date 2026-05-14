"""
Forwarding — RBI sends a complaint to the bank's Crest agent.

This is the integration moment. Pressing the "Forward to Bank" button in the
RBI staff UI fires this endpoint, which (a) calls the bank's Crest agent over
HTTP, (b) records the result, (c) updates complaint status.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_api_key
from app.db.session import get_db
from app.db.models import Complaint, ComplaintStatus, Forwarding
from app.schemas import ForwardResult
from app.services.crest_client import CrestBankClient
from app.services.audit_service import log_event

log = logging.getLogger(__name__)

router = APIRouter(prefix="/forwarding", tags=["forwarding"])


@router.post("/{complaint_id}/forward", response_model=ForwardResult)
async def forward_to_bank(
    complaint_id: str,
    actor: Annotated[str, Depends(require_api_key)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> ForwardResult:
    c = await db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found.")

    client = CrestBankClient()

    # Fire the call. Catch transport errors so we record them and don't 500.
    http_status: int | None = None
    bank_run_id: str | None = None
    error_message: str | None = None
    response_body: dict = {}

    try:
        result = await client.trigger_grievance_agent(
            complaint_reference_no=c.reference_no,
            customer_token_id=c.customer_token_id,
            channel="cms_portal",                   # always 'cms_portal' from RBI's side
            raw_text=c.raw_text,
            received_at=c.received_at.isoformat(),
            language=c.language,
        )
        http_status   = result["http_status"]
        response_body = result.get("body") or {}
        bank_run_id   = (response_body.get("run_id")
                         or response_body.get("id")
                         or response_body.get("runId"))
    except Exception as e:
        error_message = f"{type(e).__name__}: {e}"
        log.warning("Forwarding %s to bank failed: %s", c.reference_no, error_message)

    # Persist forwarding row
    f = Forwarding(
        complaint_id=c.id,
        bank_code=c.bank_code,
        http_status=http_status,
        bank_run_id=bank_run_id,
        error_message=error_message,
        payload={"request_sent": True, "response": response_body},
    )
    db.add(f)

    # Update complaint status if successful
    success = http_status is not None and 200 <= http_status < 300
    if success:
        c.status = ComplaintStatus.forwarded_to_bank

    await log_event(
        db, actor=actor,
        event_type="complaint.forwarded" if success else "complaint.forward_failed",
        outcome="success" if success else "failure",
        resource_type="complaint",
        resource_id=c.id,
        detail={
            "reference_no": c.reference_no,
            "bank_code":    c.bank_code,
            "http_status":  http_status,
            "bank_run_id":  bank_run_id,
            "error":        error_message,
        },
    )

    await db.flush()

    return ForwardResult(
        forwarding_id=f.id,
        bank_code=c.bank_code,
        bank_run_id=bank_run_id,
        http_status=http_status,
        success=success,
        detail=(
            f"Forwarded to bank {c.bank_code}; bank run id {bank_run_id}."
            if success
            else f"Forwarding failed (HTTP {http_status}, error={error_message})."
        ),
    )

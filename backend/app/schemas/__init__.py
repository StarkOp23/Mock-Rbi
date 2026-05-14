"""Pydantic v2 request/response schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import (
    ComplaintStatus, ComplaintChannel, IntentClass, BankOutcome,
)


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Complaint
# -----------------------------------------------------------------------------
class ComplaintCreate(BaseModel):
    """RBI staff lodges a new complaint."""
    customer_name:    str
    customer_email:   str | None = None
    customer_mobile:  str | None = None
    customer_token_id: str = Field(min_length=3, max_length=40)
    bank_code:        str = Field(min_length=2, max_length=10)
    channel:          ComplaintChannel
    intent_class:     IntentClass
    language:         str = Field(default="en", min_length=2, max_length=4)
    raw_text:         str = Field(min_length=10, max_length=5000)


class ComplaintRead(_ORM):
    id:                 str
    reference_no:       str
    customer_name:      str
    customer_email:     str | None
    customer_mobile:    str | None
    customer_token_id:  str
    bank_code:          str
    channel:            ComplaintChannel
    intent_class:       IntentClass
    language:           str
    raw_text:           str
    status:             ComplaintStatus
    received_at:        datetime
    closed_at:          datetime | None


class ComplaintListItem(_ORM):
    """Lighter row for the list view."""
    id:           str
    reference_no: str
    customer_name: str
    bank_code:    str
    intent_class: IntentClass
    status:       ComplaintStatus
    received_at:  datetime
    language:     str


# -----------------------------------------------------------------------------
# Forwarding
# -----------------------------------------------------------------------------
class ForwardingRead(_ORM):
    id:           str
    bank_code:    str
    forwarded_at: datetime
    http_status:  int | None
    bank_run_id:  str | None
    error_message: str | None


class ForwardResult(BaseModel):
    forwarding_id: str
    bank_code:     str
    bank_run_id:   str | None
    http_status:   int | None
    success:       bool
    detail:        str


# -----------------------------------------------------------------------------
# Bank response
# -----------------------------------------------------------------------------
class BankResponseCreate(BaseModel):
    """Bank POSTs the resolution back to RBI."""
    complaint_reference_no: str
    bank_code:        str
    outcome:          BankOutcome
    compensation_inr: float = 0
    tat_days:         int
    breached_30_day:  bool = False
    customer_letter:  str | None = None
    cited_clauses:    list[dict[str, Any]] = []
    bank_run_id:      str | None = None


class BankResponseRead(_ORM):
    id:               str
    bank_code:        str
    received_at:      datetime
    outcome:          BankOutcome
    compensation_inr: float
    tat_days:         int
    breached_30_day:  bool
    customer_letter:  str | None
    bank_run_id:      str | None


# -----------------------------------------------------------------------------
# Detail response (combined)
# -----------------------------------------------------------------------------
class ComplaintDetail(BaseModel):
    complaint:   ComplaintRead
    forwardings: list[ForwardingRead]
    responses:   list[BankResponseRead]


# -----------------------------------------------------------------------------
# Dashboard
# -----------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_complaints:        int
    by_status:               dict[str, int]
    by_bank:                 dict[str, int]
    by_intent:               dict[str, int]
    open_count:              int
    avg_tat_days:            float | None
    breach_count:            int


# -----------------------------------------------------------------------------
# Audit
# -----------------------------------------------------------------------------
class AuditEventRead(_ORM):
    id:           int
    occurred_at:  datetime
    actor:        str
    event_type:   str
    resource_type: str | None
    resource_id:  str | None
    outcome:      str
    detail:       dict

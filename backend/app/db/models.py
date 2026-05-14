"""
SQLAlchemy ORM models for the Mock RBI CMS.

Four tables:
    1. complaint        — every customer complaint lodged with RBI
    2. forwarding       — each time RBI forwards a complaint to a bank
    3. bank_response    — each resolution returned by a bank
    4. audit_event      — append-only log (mirrors Crest's audit pattern)
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, DateTime, Text, ForeignKey, Enum as SAEnum, Index,
    Numeric, Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------------------------------------------------------
# Enums (mirror RBI's CMS taxonomy)
# -----------------------------------------------------------------------------
class ComplaintStatus(str, enum.Enum):
    received          = "received"             # just lodged with RBI
    forwarded_to_bank = "forwarded_to_bank"    # sent to bank, awaiting reply
    bank_responded    = "bank_responded"       # bank has posted a resolution
    closed_satisfied  = "closed_satisfied"     # customer satisfied
    escalated_to_io   = "escalated_to_io"      # customer escalated to RBI Ombudsman
    deemed_rejected   = "deemed_rejected"      # bank failed to respond in T+30


class ComplaintChannel(str, enum.Enum):
    cms_portal_web = "cms_portal_web"
    email          = "email"
    physical_mail  = "physical_mail"
    call_center    = "call_center"


class IntentClass(str, enum.Enum):
    deficiency_in_service     = "deficiency_in_service"
    atm_card                  = "atm_card"
    mobile_internet_banking   = "mobile_internet_banking"
    mis_selling               = "mis_selling"
    loan_advances             = "loan_advances"
    pension                   = "pension"
    levy_of_charges           = "levy_of_charges"
    cheque_collection         = "cheque_collection"
    deceased_claim            = "deceased_claim"
    other                     = "other"


class BankOutcome(str, enum.Enum):
    upheld                = "upheld"
    partial               = "partial"
    rejected              = "rejected"
    insufficient_evidence = "insufficient_evidence"


# -----------------------------------------------------------------------------
# Tables
# -----------------------------------------------------------------------------
class Complaint(Base):
    __tablename__ = "complaint"

    id:           Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    reference_no: Mapped[str]      = mapped_column(String(40), unique=True, index=True)   # e.g. RBI-CMS-2026-04-00781

    # Customer info — RBI's CMS captures this and forwards a SUBSET to the bank
    customer_name:     Mapped[str]                = mapped_column(String(120))
    customer_email:    Mapped[str | None]         = mapped_column(String(120))
    customer_mobile:   Mapped[str | None]         = mapped_column(String(20))
    customer_token_id: Mapped[str]                = mapped_column(String(40), index=True)
    # ^ tokenised reference passed to the bank — bank looks this up against its CBS

    bank_code:    Mapped[str]      = mapped_column(String(10), index=True)   # e.g. HDFC, ICICI
    channel:      Mapped[ComplaintChannel] = mapped_column(SAEnum(ComplaintChannel, name="complaint_channel_t"))
    intent_class: Mapped[IntentClass]      = mapped_column(SAEnum(IntentClass,      name="intent_class_t"))
    raw_text:     Mapped[str]              = mapped_column(Text)
    language:     Mapped[str]              = mapped_column(String(4), default="en")

    status:       Mapped[ComplaintStatus] = mapped_column(
        SAEnum(ComplaintStatus, name="complaint_status_t"),
        default=ComplaintStatus.received,
        index=True,
    )

    received_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    closed_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    forwardings:  Mapped[list["Forwarding"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", lazy="selectin",
    )
    responses:    Mapped[list["BankResponse"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", lazy="selectin",
    )

    __table_args__ = (
        Index("ix_complaint_bank_status", "bank_code", "status"),
    )


class Forwarding(Base):
    __tablename__ = "forwarding"

    id:            Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    complaint_id:  Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("complaint.id", ondelete="CASCADE"), index=True)
    bank_code:     Mapped[str]      = mapped_column(String(10), index=True)
    forwarded_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Result of the HTTP POST to the bank's Crest agent
    http_status:   Mapped[int | None]      = mapped_column(Integer)
    bank_run_id:   Mapped[str | None]      = mapped_column(String(80))
    error_message: Mapped[str | None]      = mapped_column(Text)
    payload:       Mapped[dict]            = mapped_column(JSONB, default=dict)

    complaint: Mapped["Complaint"] = relationship(back_populates="forwardings")


class BankResponse(Base):
    __tablename__ = "bank_response"

    id:            Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    complaint_id:  Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("complaint.id", ondelete="CASCADE"), index=True)
    bank_code:     Mapped[str]      = mapped_column(String(10))
    received_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    outcome:           Mapped[BankOutcome]   = mapped_column(SAEnum(BankOutcome, name="bank_outcome_t"))
    compensation_inr:  Mapped[float]         = mapped_column(Numeric(12, 2), default=0)
    tat_days:          Mapped[int]           = mapped_column(Integer)
    breached_30_day:   Mapped[bool]          = mapped_column(Boolean, default=False)
    customer_letter:   Mapped[str | None]    = mapped_column(Text)
    cited_clauses:     Mapped[list]          = mapped_column(JSONB, default=list)
    bank_run_id:       Mapped[str | None]    = mapped_column(String(80))
    raw_payload:       Mapped[dict]          = mapped_column(JSONB, default=dict)

    complaint: Mapped["Complaint"] = relationship(back_populates="responses")


class AuditEvent(Base):
    """Append-only audit ledger — every action on the mock RBI side."""
    __tablename__ = "audit_event"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    actor:        Mapped[str]      = mapped_column(String(80))         # rbi_staff, system, bank-API
    event_type:   Mapped[str]      = mapped_column(String(60), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id:  Mapped[str | None]  = mapped_column(String(80), index=True)
    outcome:      Mapped[str]      = mapped_column(String(20))         # success | failure
    detail:       Mapped[dict]     = mapped_column(JSONB, default=dict)

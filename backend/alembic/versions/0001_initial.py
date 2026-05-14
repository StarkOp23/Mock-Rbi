"""initial schema — complaint, forwarding, bank_response, audit_event

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-29 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- ENUMs ----
    op.execute("""
        CREATE TYPE complaint_status_t AS ENUM (
            'received', 'forwarded_to_bank', 'bank_responded',
            'closed_satisfied', 'escalated_to_io', 'deemed_rejected'
        );
    """)
    op.execute("""
        CREATE TYPE complaint_channel_t AS ENUM (
            'cms_portal_web', 'email', 'physical_mail', 'call_center'
        );
    """)
    op.execute("""
        CREATE TYPE intent_class_t AS ENUM (
            'deficiency_in_service', 'atm_card', 'mobile_internet_banking',
            'mis_selling', 'loan_advances', 'pension', 'levy_of_charges',
            'cheque_collection', 'deceased_claim', 'other'
        );
    """)
    op.execute("""
        CREATE TYPE bank_outcome_t AS ENUM (
            'upheld', 'partial', 'rejected', 'insufficient_evidence'
        );
    """)

    # ---- complaint ----
    op.create_table(
        "complaint",
        sa.Column("id",                postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("reference_no",      sa.String(40),  unique=True, index=True, nullable=False),
        sa.Column("customer_name",     sa.String(120), nullable=False),
        sa.Column("customer_email",    sa.String(120)),
        sa.Column("customer_mobile",   sa.String(20)),
        sa.Column("customer_token_id", sa.String(40), nullable=False, index=True),
        sa.Column("bank_code",         sa.String(10), nullable=False, index=True),
        sa.Column("channel",           postgresql.ENUM(name="complaint_channel_t", create_type=False), nullable=False),
        sa.Column("intent_class",      postgresql.ENUM(name="intent_class_t",      create_type=False), nullable=False),
        sa.Column("raw_text",          sa.Text(), nullable=False),
        sa.Column("language",          sa.String(4), nullable=False, server_default="en"),
        sa.Column("status",            postgresql.ENUM(name="complaint_status_t", create_type=False),
                  nullable=False, server_default="received", index=True),
        sa.Column("received_at",       sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("closed_at",         sa.DateTime(timezone=True)),
    )
    op.create_index("ix_complaint_bank_status", "complaint", ["bank_code", "status"])

    # ---- forwarding ----
    op.create_table(
        "forwarding",
        sa.Column("id",            postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("complaint_id",  postgresql.UUID(as_uuid=False),
                  sa.ForeignKey("complaint.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bank_code",     sa.String(10), nullable=False, index=True),
        sa.Column("forwarded_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status",   sa.Integer()),
        sa.Column("bank_run_id",   sa.String(80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("payload",       postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    # ---- bank_response ----
    op.create_table(
        "bank_response",
        sa.Column("id",               postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("complaint_id",     postgresql.UUID(as_uuid=False),
                  sa.ForeignKey("complaint.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bank_code",        sa.String(10), nullable=False),
        sa.Column("received_at",      sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("outcome",          postgresql.ENUM(name="bank_outcome_t", create_type=False), nullable=False),
        sa.Column("compensation_inr", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tat_days",         sa.Integer(), nullable=False),
        sa.Column("breached_30_day",  sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("customer_letter",  sa.Text()),
        sa.Column("cited_clauses",    postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("bank_run_id",      sa.String(80)),
        sa.Column("raw_payload",      postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    # ---- audit_event ----
    op.create_table(
        "audit_event",
        sa.Column("id",            sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("occurred_at",   sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("actor",         sa.String(80), nullable=False),
        sa.Column("event_type",    sa.String(60), nullable=False, index=True),
        sa.Column("resource_type", sa.String(40)),
        sa.Column("resource_id",   sa.String(80), index=True),
        sa.Column("outcome",       sa.String(20), nullable=False),
        sa.Column("detail",        postgresql.JSONB(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("audit_event")
    op.drop_table("bank_response")
    op.drop_table("forwarding")
    op.drop_table("complaint")
    op.execute("DROP TYPE bank_outcome_t")
    op.execute("DROP TYPE intent_class_t")
    op.execute("DROP TYPE complaint_channel_t")
    op.execute("DROP TYPE complaint_status_t")

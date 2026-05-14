"""
Seed the mock RBI CMS with realistic sample complaints.

Run via: docker compose exec backend python -m app.db.seed
Or automatically on container start (Dockerfile CMD).

Idempotent: skips if data already present.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import (
    Complaint, ComplaintStatus, ComplaintChannel, IntentClass,
    AuditEvent,
)


SAMPLES = [
    {
        "reference_no":      "RBI-CMS-2026-04-00781",
        "customer_name":     "Anjali Deshpande",
        "customer_email":    "anjali.deshpande@example.com",
        "customer_mobile":   "+919822001234",
        "customer_token_id": "CUST-9912034",
        "bank_code":         "HDFC",
        "channel":           ComplaintChannel.cms_portal_web,
        "intent_class":      IntentClass.atm_card,
        "language":          "en",
        "raw_text":          "ATM at Pimpri branch debited Rs 5,000 on 12-Apr-2026 but cash was not dispensed. I reported it the same day. It has been 18 days and no reversal has happened.",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00795",
        "customer_name":     "Vikrant Mehta",
        "customer_email":    "vikrant.mehta@example.com",
        "customer_mobile":   "+919811234567",
        "customer_token_id": "CUST-5512876",
        "bank_code":         "HDFC",
        "channel":           ComplaintChannel.email,
        "intent_class":      IntentClass.levy_of_charges,
        "language":          "en",
        "raw_text":          "I paid my credit card bill on the due date through net banking but a late fee of Rs 500 plus GST was charged. Bank says payment received next day.",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00802",
        "customer_name":     "Sunita Kumari",
        "customer_email":    "sunita.kumari@example.com",
        "customer_mobile":   "+919199876543",
        "customer_token_id": "CUST-3398421",
        "bank_code":         "ICICI",
        "channel":           ComplaintChannel.cms_portal_web,
        "intent_class":      IntentClass.deficiency_in_service,
        "language":          "hi",
        "raw_text":          "मेरी शाखा में कर्मचारियों का व्यवहार ठीक नहीं है। पासबुक अपडेट कराने में 2 घंटे लगे।",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00810",
        "customer_name":     "Ramesh Iyer",
        "customer_email":    "ramesh.iyer@example.com",
        "customer_mobile":   "+919445098712",
        "customer_token_id": "CUST-7745210",
        "bank_code":         "HDFC",
        "channel":           ComplaintChannel.physical_mail,
        "intent_class":      IntentClass.cheque_collection,
        "language":          "en",
        "raw_text":          "Cheque deposited on 15-Mar-2026 for Rs 2,50,000 has not been credited even after 30 days. As a senior citizen, I depend on this for medical expenses.",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00815",
        "customer_name":     "Prakash Joshi",
        "customer_email":    "prakash.joshi@example.com",
        "customer_mobile":   "+919823456789",
        "customer_token_id": "CUST-3398422",
        "bank_code":         "HDFC",
        "channel":           ComplaintChannel.cms_portal_web,
        "intent_class":      IntentClass.loan_advances,
        "language":          "mr",
        "raw_text":          "गृहकर्जाच्या व्याजदरात बदल झाला आहे पण मला कोणतीही पूर्व सूचना दिली नाही. EMI अचानक वाढली.",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00820",
        "customer_name":     "Lakshmi Subramanian",
        "customer_email":    "lakshmi.s@example.com",
        "customer_mobile":   "+919442233445",
        "customer_token_id": "CUST-7745211",
        "bank_code":         "SBI",
        "channel":           ComplaintChannel.call_center,
        "intent_class":      IntentClass.pension,
        "language":          "ta",
        "raw_text":          "ஓய்வூதியம் கடந்த 2 மாதங்களாக வரவில்லை. வங்கி கிளையில் கேட்டபோது சரியான பதில் இல்லை.",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00825",
        "customer_name":     "Iqbal Khan",
        "customer_email":    "iqbal.khan@example.com",
        "customer_mobile":   "+919112223344",
        "customer_token_id": "CUST-8800012",
        "bank_code":         "HDFC",
        "channel":           ComplaintChannel.email,
        "intent_class":      IntentClass.mobile_internet_banking,
        "language":          "en",
        "raw_text":          "My net-banking account has been blocked for 10 days without any explanation. I have provided KYC documents twice.",
        "status":            ComplaintStatus.received,
    },
    {
        "reference_no":      "RBI-CMS-2026-04-00830",
        "customer_name":     "Karthik Foods Pvt Ltd",
        "customer_email":    "finance@karthikfoods.example",
        "customer_mobile":   "+918012345678",
        "customer_token_id": "CUST-6610099",
        "bank_code":         "ICICI",
        "channel":           ComplaintChannel.email,
        "intent_class":      IntentClass.deficiency_in_service,
        "language":          "en",
        "raw_text":          "Trade finance application submitted 45 days ago has not been processed. Multiple follow-ups have not received any response.",
        "status":            ComplaintStatus.received,
    },
]


async def seed():
    async with session_scope() as session:
        # Idempotency check
        existing = await session.scalar(select(Complaint).limit(1))
        if existing:
            print(f"[seed] already seeded — skipping")
            return

        now = datetime.now(timezone.utc)
        for i, s in enumerate(SAMPLES):
            # Stagger received_at across the last 14 days for a believable timeline
            received_at = now - timedelta(days=14 - i, hours=i * 3)
            complaint = Complaint(received_at=received_at, **s)
            session.add(complaint)

        session.add(AuditEvent(
            actor="system",
            event_type="seed.completed",
            outcome="success",
            detail={"complaints_seeded": len(SAMPLES)},
        ))

        print(f"[seed] inserted {len(SAMPLES)} complaints")


if __name__ == "__main__":
    asyncio.run(seed())

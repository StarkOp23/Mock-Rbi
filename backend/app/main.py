"""
Mock RBI CMS Portal — FastAPI app.

Demo URL (via nginx):    http://localhost:8090
Direct backend (dev):    http://localhost:8088
OpenAPI docs:            http://localhost:8088/docs
Health:                  http://localhost:8088/api/v1/health
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import health, complaints, forwarding, responses, audit


logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


app = FastAPI(
    title="Mock RBI CMS Portal",
    description=(
        "A standalone mock of the Reserve Bank of India's Complaints Management "
        "System (CMS) used to drive end-to-end demos of the Crest.ai Customer "
        "Grievance & Internal Ombudsman Agent. RBI staff lodge complaints here; "
        "this service forwards them to the bank's Crest agent over HTTP and "
        "receives back the bank's resolution."
    ),
    version="1.0.0",
)

# CORS — open in dev/demo. In production, restrict to the bank's UI origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router,      prefix="/api/v1")
app.include_router(complaints.router,  prefix="/api/v1")
app.include_router(complaints.dashboard_router, prefix="/api/v1")
app.include_router(forwarding.router,  prefix="/api/v1")
app.include_router(responses.router,   prefix="/api/v1")
app.include_router(audit.router,       prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    return {
        "service": "mock-rbi-cms",
        "version": app.version,
        "docs":    "/docs",
        "api":     "/api/v1",
    }

"""
HTTP client to the bank-side Crest agent.

This is the integration point. RBI CMS forwards a complaint to the bank by
calling the bank's Crest agent's trigger endpoint:

    POST {CREST_BANK_BASE_URL}/api/v1/agents/{CREST_BANK_AGENT_ID}/runs
    Authorization: Bearer {CREST_BANK_API_KEY}
    Content-Type: application/json
    {
      "input_payload": { ... trigger payload matching the agent's input_schema ... },
      "trigger_type":  "api"
    }

The shape of the trigger payload exactly matches the input_schema declared
in the cgio_agent_crest.json that we built earlier. Don't change it without
also updating the agent's Trigger node config.
"""
import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)


class CrestBankClient:
    """Async client to a single bank's Crest grievance agent."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key:  str | None = None,
        agent_id: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.CREST_BANK_BASE_URL).rstrip("/")
        self.api_key  = api_key  or settings.CREST_BANK_API_KEY
        self.agent_id = agent_id or settings.CREST_BANK_AGENT_ID
        self.timeout  = timeout_seconds

    async def trigger_grievance_agent(
        self,
        complaint_reference_no: str,
        customer_token_id:      str,
        channel:                str,
        raw_text:               str,
        received_at:            str,
        language:               str = "en",
    ) -> dict[str, Any]:
        """
        Fire the Crest agent. Returns the agent's response payload — usually
        contains run_id and initial status.

        Raises httpx.HTTPError on transport failure; caller logs it as a
        forwarding error and continues (the complaint stays open in the
        mock RBI side and can be retried).
        """
        # FIXED: plural "runs" (was singular "run")
        url = f"{self.base_url}/api/v1/agents/{self.agent_id}/runs"

        # FIXED: outer key is "input_payload" (was "input"), and "trigger_type" added.
        # FIXED: inner field is "query" (was "raw_text") so the RAG node's
        # _extract_query() finds the question on its first lookup.
        payload = {
            "input_payload": {
                "complaint_id":   complaint_reference_no,
                "channel":        channel,
                "customer_id":    customer_token_id,
                "query":          raw_text,
                "attachments":    [],
                "received_at":    received_at,
                "language":       language,
            },
            "trigger_type": "api",
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "X-Caller":      "mock-rbi-cms",
        }

        log.info("Posting complaint %s to Crest agent at %s", complaint_reference_no, url)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return {
                "http_status": resp.status_code,
                "body":        _safe_json(resp),
                "url":         url,
            }


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw_text": resp.text[:1000]}

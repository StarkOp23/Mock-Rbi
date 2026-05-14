# Crest Integration Guide

This folder contains the artefacts that wire the bank-side Crest agent to this Mock RBI CMS Portal.

## The two integration points

```
   Mock RBI CMS                                   Bank-side Crest Agent
   ───────────                                    ──────────────────────

   ① RBI staff clicks "Forward to Bank"  ───POST──▶  /api/v1/agents/{id}/run
      (configured via CREST_BANK_BASE_URL)             (Trigger node fires)

                                                       … agent runs DAG …

   ② /api/v1/responses  ◀──POST──  Notification node (Node 13/14) fires
      (this connection.json)                          at end of bank workflow
```

## Files

| File | Purpose |
|---|---|
| `connection.json` | Paste into Crest **Connections → Add Connection** as a `rest_api` connection. The bank-side agent uses this to call back to RBI when the customer letter is sent. |
| `trigger-payload-sample.json` | The exact payload the bank's Crest **Trigger node** receives when RBI forwards a complaint. Matches the `input_schema` in `cgio_agent_crest.json`. |
| `curl-tests.sh` | End-to-end smoke test. Runs against this Mock RBI; works without a real Crest agent (forwarding will fail at the bank-side leg, which is expected). |
| `mock-bank-callback.sh` | Simulates the bank posting back its resolution. Use this to demo the full RBI → bank → RBI round-trip when no Crest agent is running. |

## How to use during a demo

### Scenario A — Mock RBI alone (no Crest needed)

```bash
# 1. Lodge or pick a complaint via the UI at http://localhost:8090
# 2. Forward it (will record a forwarding error since no bank agent is up)
# 3. Simulate the bank's response:
./mock-bank-callback.sh RBI-CMS-2026-04-00781 upheld 6100
# 4. Reload the complaint page — see status = bank_responded with the letter
```

### Scenario B — Mock RBI + real Crest agent

```bash
# 1. Start your Crest stack on its usual ports (8000 backend)
# 2. Import cgio_agent_crest.json into the Crest Agent Studio
# 3. Add the rbi-cms-callback connection from connection.json
# 4. Wire it into Node 13/14 of the agent
# 5. Start mock RBI (this stack)
# 6. From the Mock RBI UI, click "Forward to Bank"
# 7. Watch the Crest agent run end-to-end via its run-detail page
# 8. Bank-side agent posts back to /api/v1/responses
# 9. Mock RBI shows status = bank_responded with the customer letter
```

## Authentication

- Mock RBI uses a single Bearer token, set in `RBI_API_KEY`. Default: `rbi_demo_token_change_me`.
- The Crest connection's `credential_label` should map to whatever credential alias your Crest deployment uses.
- All requests in either direction carry an `X-Caller` header so audit logs can attribute them.

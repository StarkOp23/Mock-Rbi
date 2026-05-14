# Mock RBI CMS Portal

A standalone, runnable mock of the Reserve Bank of India's **Complaints Management System (CMS) Portal**, built to demo end-to-end integration with a bank's Crest.ai Customer Grievance & Internal Ombudsman Agent.

## What it is

A two-sided live demo:

```
   Mock RBI CMS                         Bank-side Crest Agent
   (this repo)                          (cgio_agent_crest.json)

   ┌──────────────────────┐             ┌─────────────────────────┐
   │  React UI for        │             │  Crest workflow agent   │
   │  RBI staff           │             │  (15 nodes, full DAG)   │
   │                      │             │                         │
   │  FastAPI backend     │ ──forward─▶ │  Trigger → Intent →     │
   │  Postgres database   │             │  RAG → LLM → HITL →     │
   │  Audit log           │ ◀─response─ │  Notification → Output  │
   └──────────────────────┘             └─────────────────────────┘
            ↑                                        ↑
   Demonstrated by RBI staff                Demonstrated as a real
   logging in to the mock UI                Crest agent run
```

This means a single demo can show: an RBI officer lodging a customer complaint, forwarding it to a bank, watching the bank's Crest agent process it through its full DAG (with LLM reasoning, RAG citations, human-in-the-loop approval), and then seeing the bank's resolution land back in the RBI dashboard.

## Stack

Mirrors the Crest.ai platform stack so that both sides can be deployed identically:

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI (async) |
| ORM | SQLAlchemy 2.x async + Alembic migrations |
| Database | PostgreSQL 16 |
| Frontend | React 18 + TypeScript + Vite |
| Reverse proxy | Nginx |
| Container orchestration | Docker Compose |

## Quick start

```bash
# 1. Clone / unpack
cd mock-rbi-cms

# 2. Copy the env template (defaults work for a local demo)
cp .env.example .env

# 3. Bring up the stack
docker compose up -d --build

# 4. Wait ~20 seconds for postgres + alembic migrations + seed
docker compose logs -f backend     # ctrl-c when you see "Application startup complete"

# 5. Open the UI
open http://localhost:8090         # macOS
# or visit http://localhost:8090 in any browser

# 6. (Optional) hit the API directly
curl -H "Authorization: Bearer rbi_demo_token_change_me" \
     http://localhost:8088/api/v1/health

# 7. (Optional) end-to-end smoke test
chmod +x crest-integration/curl-tests.sh
./crest-integration/curl-tests.sh
```

### Ports

| Port | What |
|---|---|
| 8090 | RBI staff UI (this is the demo URL) |
| 8088 | FastAPI backend (direct, for API/Swagger access) |
| 5433 | Postgres (host port; container internal is 5432) |

Ports are deliberately offset from Crest's defaults (8000 / 5432) so both stacks can run side-by-side on the same laptop.

## Demo script (5 minutes)

### Scene 1 — RBI receives a complaint
1. Visit http://localhost:8090
2. Sidebar → **New Complaint**
3. Fill in: customer name, CBS token (e.g. `CUST-9912034`), bank `HDFC`, intent `atm_card`, language `en`, paste a complaint description
4. Click **Lodge Complaint**

### Scene 2 — RBI forwards to the bank
5. You land on the complaint detail page; the status badge says **received**
6. Click **→ Forward to Bank**
7. The mock RBI POSTs the complaint to the bank's Crest agent
8. Status badge moves to **forwarded to bank**
9. Forwarding History shows HTTP status + bank's run ID

### Scene 3 — Bank resolves and posts back

If the bank's Crest agent is running and wired up: it processes the complaint through its DAG and the agent's final notification node POSTs back to `/api/v1/responses`.

If you're demoing the RBI side alone, simulate it:

```bash
./crest-integration/mock-bank-callback.sh RBI-CMS-2026-04-XXXXX upheld 6100
```

### Scene 4 — RBI sees resolution
10. Refresh the complaint detail page
11. Status moves to **bank responded**, the bank's outcome and customer letter appear
12. Sidebar → **Bank Responses** shows it in the inbox view
13. Sidebar → **Audit Log** shows every action since lodging

## Architecture

```
mock-rbi-cms/
├── docker-compose.yml          ← orchestration
├── .env.example
│
├── backend/                    ← FastAPI + async SQLAlchemy
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              ← async-aware Alembic env
│   │   └── versions/
│   │       └── 0001_initial.py ← schema migration
│   └── app/
│       ├── main.py             ← FastAPI app
│       ├── config.py           ← env settings
│       ├── auth.py             ← Bearer-token guard
│       ├── db/
│       │   ├── session.py
│       │   ├── models.py       ← Complaint, Forwarding, BankResponse, AuditEvent
│       │   └── seed.py         ← 8 multilingual sample complaints
│       ├── schemas/
│       │   └── __init__.py     ← Pydantic v2 models
│       ├── services/
│       │   ├── crest_client.py ← HTTP client to bank-side Crest agent
│       │   └── audit_service.py
│       └── api/v1/
│           ├── health.py
│           ├── complaints.py   ← CRUD + dashboard
│           ├── forwarding.py   ← POST → bank Crest agent
│           ├── responses.py    ← bank posts back resolution
│           └── audit.py
│
├── frontend/                   ← React 18 + TypeScript
│   ├── Dockerfile
│   ├── package.json, tsconfig.json, vite.config.ts
│   ├── nginx-spa.conf
│   ├── index.html
│   └── src/
│       ├── main.tsx, App.tsx
│       ├── styles.css          ← refined institutional aesthetic
│       ├── api/client.ts       ← typed API client
│       └── pages/              ← Dashboard, Intake, List, Detail, Inbox, Audit
│
├── nginx/
│   └── nginx.conf              ← /api proxy + auth header injection
│
└── crest-integration/
    ├── README.md               ← integration-specific notes
    ├── connection.json         ← Crest connection definition
    ├── trigger-payload-sample.json
    ├── curl-tests.sh           ← end-to-end smoke test
    └── mock-bank-callback.sh   ← simulate the bank's resolution
```

## Database schema

| Table | Purpose |
|---|---|
| `complaint` | One row per customer complaint received by RBI. Includes customer info, bank, intent, raw text, and lifecycle status. |
| `forwarding` | One row per attempt to forward a complaint to a bank's Crest agent. Captures HTTP status and bank's run ID. |
| `bank_response` | One row per resolution returned by a bank. Captures outcome, compensation, TAT, customer letter, cited clauses. |
| `audit_event` | Append-only ledger of every significant action — mirrors the audit pattern used inside Crest. |

The schema lives in `backend/alembic/versions/0001_initial.py`. To inspect it after launch:

```bash
docker compose exec postgres psql -U rbi_user -d rbi_cms -c "\dt"
```

## Seeded data

The backend container runs `app/db/seed.py` on first startup. It creates 8 sample complaints across multiple banks, languages, and intent classes — including the `CUST-9912034` ATM debit case used in the Crest agent's test fixtures.

The seed is idempotent — restarting won't duplicate.

To re-seed from scratch:

```bash
docker compose down -v   # destroys the postgres volume
docker compose up -d --build
```

## API surface

Full OpenAPI / Swagger docs at: **http://localhost:8088/docs**

Key endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Health probe |
| POST | `/api/v1/complaints` | Lodge a new complaint |
| GET | `/api/v1/complaints` | List, filterable by bank/status/intent |
| GET | `/api/v1/complaints/{id}` | Full detail incl. forwardings + responses |
| GET | `/api/v1/complaints/by-ref/{ref}` | Look up by reference number |
| POST | `/api/v1/forwarding/{id}/forward` | Forward a complaint to the bank's Crest agent |
| POST | `/api/v1/responses` | Bank's Crest agent posts back the resolution |
| GET | `/api/v1/dashboard/stats` | KPI tiles |
| GET | `/api/v1/audit` | Browse the audit log |

Authentication: every endpoint requires `Authorization: Bearer <RBI_API_KEY>`. Default token: `rbi_demo_token_change_me`.

## Configuration

Edit `.env` (created from `.env.example`):

| Variable | Default | Notes |
|---|---|---|
| `POSTGRES_DB` | `rbi_cms` | |
| `POSTGRES_USER` | `rbi_user` | |
| `POSTGRES_PASSWORD` | `rbi_pass_demo_only` | **Change for any non-demo use** |
| `RBI_API_KEY` | `rbi_demo_token_change_me` | **Change for any non-demo use** |
| `CREST_BANK_BASE_URL` | `http://host.docker.internal:8000` | Where the bank's Crest backend listens |
| `CREST_BANK_API_KEY` | `crest_test_sk_demo` | Bank's Crest API key |
| `CREST_BANK_AGENT_ID` | `grievance-io-agent` | Slug of the bank's Crest agent |

## Troubleshooting

**`docker compose up` says port 8090 / 8088 / 5433 in use**
Edit the host-side ports in `docker-compose.yml` (left of the colon) to free values.

**Forwarding always fails with `Connection refused`**
Expected when no bank-side Crest agent is running. The forwarding row is still recorded; use `mock-bank-callback.sh` to simulate the bank's reply.

**Hindi / Tamil / Marathi text shows as boxes in the UI**
Browser font fallback. The React app uses system fonts for Indic scripts; install Noto Sans Devanagari / Tamil / etc. on the demo machine if needed.

**Backend container restart loops**
```powershell
docker logs mock-rbi-backend --tail 50
```
The entrypoint prints a clear diagnostic before failing. The two most common causes:

1. **`InvalidPasswordError: password authentication failed for user "rbi_user"`** —
   The Postgres data volume was initialised previously with a *different* password.
   Postgres only honours `POSTGRES_PASSWORD` on first init of an empty data
   directory; afterwards it ignores the env var and uses whatever password is
   stored inside the database. **Fix — wipe the volume:**
   ```powershell
   docker compose down -v          # the -v is critical
   docker compose up -d --build
   ```
   On PowerShell 5.1 (Windows), `&&` doesn't work as a chain operator — run
   the two commands on separate lines, or use `;` to chain them.

2. **Migrations failed against a partial schema from a previous version** —
   Same fix as above: `docker compose down -v && docker compose up -d --build`.

**`exec /app/entrypoint.sh: no such file or directory`**
The entrypoint script was checked out on Windows with CRLF line endings.
The Dockerfile runs `dos2unix` to fix this automatically — make sure you've
done a fresh `docker compose build` after any change to the script.

## What this is NOT

- This is a **demo mock**, not a security-hardened production service. Bearer token is a single static string; CORS is wide open; HTTPS is not configured.
- It does **not** mock RBS / SPARC submissions or the Master Direction feed — only the CMS Portal complaint-forwarding surface. Those would be future modules.

## Companion artefacts

This mock is part of a larger Crest.ai pilot bundle:

| File | Purpose |
|---|---|
| `cgio_agent_design.docx` | Full agent design document |
| `cgio_agent_crest.json` | Crest-importable agent definition (15 nodes) |
| `v_customer_360.sql` | Bank-side read schema |
| `rbs_quarterly_register.sql` | Bank-side write schema for Node 15 |
| `node_prompts.json` / `node_prompts_spec.docx` | Production-grade prompts and schemas for Nodes 8 & 10 |
| **`mock-rbi-cms/`** | **This repo — RBI counterpart** |

## License & attribution

For demo and pilot use only. Not affiliated with the Reserve Bank of India.

— OMFYS Technologies India Pvt. Ltd. · Crest.ai Pilot, April 2026

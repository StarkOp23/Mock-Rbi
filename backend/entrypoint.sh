#!/bin/sh
# =============================================================================
# Mock RBI CMS — backend entrypoint
#
# Provides:
#   1. Banner showing what we'll connect with (password length + hash prefix
#      — never the password itself)
#   2. Wait-for-Postgres loop (60s budget)
#   3. On password-auth failure: print full diagnostics so the operator can
#      tell whether it's a stale-volume issue OR a config mismatch
#   4. Idempotent migration + seed
#   5. uvicorn
# =============================================================================
set -e

log() { printf '[entrypoint] %s\n' "$*"; }
err() { printf '[entrypoint][ERROR] %s\n' "$*" >&2; }

log "================================================================"
log "Mock RBI CMS backend starting"
log "POSTGRES_HOST=${POSTGRES_HOST}  PORT=${POSTGRES_PORT}"
log "POSTGRES_USER=${POSTGRES_USER}  DB=${POSTGRES_DB}"
log "================================================================"

# Wait for Postgres + run a real auth handshake.
python - <<'PY'
import os, sys, time, asyncio, hashlib
import asyncpg

host = os.environ.get("POSTGRES_HOST", "postgres")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
user = os.environ.get("POSTGRES_USER", "rbi_user")
pw   = os.environ.get("POSTGRES_PASSWORD", "")
db   = os.environ.get("POSTGRES_DB", "rbi_cms")

# Print fingerprint of the password the BACKEND has — never the password
# itself. The operator can compare this fingerprint against what they expect.
fp = hashlib.sha256(pw.encode()).hexdigest()[:12] if pw else "(empty)"
print(f"[entrypoint] backend pw len={len(pw)} sha256_prefix={fp}")

import socket

def tcp_open(h, p, timeout=2):
    try:
        with socket.create_connection((h, p), timeout=timeout):
            return True
    except OSError:
        return False

deadline = time.time() + 60
last_err = None
auth_failed = False

while time.time() < deadline:
    # Stage 1: wait for the TCP port to accept connections at all.
    if not tcp_open(host, port):
        last_err = ConnectionError(f"{host}:{port} not yet accepting connections")
        time.sleep(2)
        continue

    # Stage 2: TCP is open — try a real auth handshake in a FRESH event loop.
    try:
        loop = asyncio.new_event_loop()
        try:
            conn = loop.run_until_complete(
                asyncpg.connect(host=host, port=port, user=user,
                                password=pw, database=db)
            )
            loop.run_until_complete(conn.close())
        finally:
            loop.close()
        print("[entrypoint] Postgres accepted our credentials.")
        sys.exit(0)
    except asyncpg.exceptions.InvalidPasswordError as e:
        auth_failed = True
        last_err = e
        break
    except asyncpg.exceptions.InvalidCatalogNameError as e:
        # DB "rbi_cms" not yet created — postgres still running init scripts.
        last_err = e
        time.sleep(2)
    except Exception as e:
        last_err = e
        time.sleep(2)

# ---- Failure path ----------------------------------------------------------
print("", file=sys.stderr)
print("=" * 70, file=sys.stderr)

if auth_failed:
    print("FATAL: Postgres rejected our password.", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print(f"Backend tried to connect as: {user}@{host}:{port}/{db}", file=sys.stderr)
    print(f"Backend's password fingerprint: sha256[:12] = {fp}", file=sys.stderr)
    print(f"Backend's password length: {len(pw)} chars", file=sys.stderr)
    print("", file=sys.stderr)
    print("To diagnose, compare this fingerprint against what Postgres", file=sys.stderr)
    print("actually has. Run from your host shell:", file=sys.stderr)
    print("", file=sys.stderr)
    print("    docker exec mock-rbi-postgres \\", file=sys.stderr)
    print("        sh -c 'printf %s \"$POSTGRES_PASSWORD\" | sha256sum | cut -c1-12'", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"If that prints '{fp}' → both sides agree. The issue is then a", file=sys.stderr)
    print("STALE VOLUME (Postgres data dir was initialised with an OLDER", file=sys.stderr)
    print("password and ignores POSTGRES_PASSWORD on subsequent restarts).", file=sys.stderr)
    print("Fix:  docker compose down -v   (the -v wipes the volume)", file=sys.stderr)
    print("      docker compose up -d --build", file=sys.stderr)
    print("", file=sys.stderr)
    print("If it prints something DIFFERENT → the env var disagrees between", file=sys.stderr)
    print("the two containers. Check your .env file, and check whether your", file=sys.stderr)
    print("shell has a stray  $env:POSTGRES_PASSWORD  set:", file=sys.stderr)
    print("    Get-ChildItem Env:POSTGRES_PASSWORD", file=sys.stderr)
    print("    Remove-Item Env:POSTGRES_PASSWORD", file=sys.stderr)
else:
    print(f"FATAL: Postgres did not become ready within 60s.", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print(f"Last error: {last_err!r}", file=sys.stderr)

print("=" * 70, file=sys.stderr)
sys.exit(2 if auth_failed else 3)
PY

log "Running alembic upgrade head..."
if ! alembic upgrade head; then
    err "Alembic migration failed."
    exit 4
fi
log "Migrations complete."

log "Seeding sample data (idempotent)..."
if ! python -m app.db.seed; then
    err "Seeding failed but continuing — re-run manually with:"
    err "  docker compose exec backend python -m app.db.seed"
fi

log "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

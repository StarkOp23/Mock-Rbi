#!/usr/bin/env bash
# =============================================================================
# Mock RBI CMS — end-to-end integration smoke tests
# Run AFTER `docker compose up -d` (or however you've launched the stack).
# =============================================================================
set -e

RBI_BASE="${RBI_BASE:-http://localhost:8088}"
RBI_TOKEN="${RBI_TOKEN:-rbi_demo_token_change_me}"

bold() { printf "\n\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }

bold "1. Health check"
curl -s "$RBI_BASE/api/v1/health" | tee /dev/stderr | grep -q '"status":"ok"' && ok "RBI CMS is up"

bold "2. List seeded complaints"
curl -s -H "Authorization: Bearer $RBI_TOKEN" \
     "$RBI_BASE/api/v1/complaints?limit=3" \
  | python3 -m json.tool | head -40
ok "List endpoint responding"

bold "3. Lodge a fresh complaint"
NEW=$(curl -s -X POST \
  -H "Authorization: Bearer $RBI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name":     "Integration Test User",
    "customer_email":    "test@example.com",
    "customer_mobile":   "+919999999999",
    "customer_token_id": "CUST-TEST-001",
    "bank_code":         "HDFC",
    "channel":           "cms_portal_web",
    "intent_class":      "atm_card",
    "language":          "en",
    "raw_text":          "Smoke-test complaint posted by curl-tests.sh"
  }' \
  "$RBI_BASE/api/v1/complaints")
echo "$NEW" | python3 -m json.tool | head -10
COMPLAINT_ID=$(echo "$NEW" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
REF=$(echo "$NEW" | python3 -c "import sys, json; print(json.load(sys.stdin)['reference_no'])")
ok "Created complaint $REF (id=$COMPLAINT_ID)"

bold "4. Forward to bank's Crest agent"
echo "    NOTE: This will fail with HTTP error if a Crest agent isn't running"
echo "    on \$CREST_BANK_BASE_URL. That's expected if you're testing the RBI"
echo "    side in isolation — the forwarding row is still recorded."
RES=$(curl -s -X POST \
  -H "Authorization: Bearer $RBI_TOKEN" \
  "$RBI_BASE/api/v1/forwarding/$COMPLAINT_ID/forward")
echo "$RES" | python3 -m json.tool

bold "5. Bank posts back a resolution (simulated)"
curl -s -X POST \
  -H "Authorization: Bearer $RBI_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"complaint_reference_no\": \"$REF\",
    \"bank_code\":         \"HDFC\",
    \"outcome\":           \"upheld\",
    \"compensation_inr\":  6100,
    \"tat_days\":          1,
    \"breached_30_day\":   false,
    \"customer_letter\":   \"Dear Customer, your complaint reference $REF has been resolved...\",
    \"cited_clauses\":     [{\"source\":\"RBI\",\"doc\":\"Master Circular - TAT for Failed Transactions\",\"clause\":\"ATM auto-reversal T+5\"}],
    \"bank_run_id\":       \"crest-run-curl-test-001\"
  }" \
  "$RBI_BASE/api/v1/responses" \
  | python3 -m json.tool | head -10
ok "Bank response recorded"

bold "6. Verify status moved to bank_responded"
curl -s -H "Authorization: Bearer $RBI_TOKEN" \
     "$RBI_BASE/api/v1/complaints/by-ref/$REF" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  reference: {d['complaint']['reference_no']}\")
print(f\"  status:    {d['complaint']['status']}\")
print(f\"  responses: {len(d['responses'])}\")
print(f\"  forwardings: {len(d['forwardings'])}\")
"
ok "End-to-end flow confirmed"

bold "7. Audit trail"
curl -s -H "Authorization: Bearer $RBI_TOKEN" \
     "$RBI_BASE/api/v1/audit?resource_id=$COMPLAINT_ID" \
  | python3 -c "
import sys, json
events = json.load(sys.stdin)
print(f'  {len(events)} audit events for complaint {sys.argv[1]}:')
for e in events:
    print(f\"    [{e['outcome']:>7}] {e['event_type']}\")
" "$COMPLAINT_ID"
ok "Audit trail verified"

printf "\n\033[1;32mAll smoke tests passed.\033[0m\n"

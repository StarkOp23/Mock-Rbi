#!/usr/bin/env bash
# =============================================================================
# Mock RBI CMS — Bank Callback Simulator
#
# Pretends to be the bank's Crest agent posting a final resolution back to
# RBI. Useful when you want to demo the FULL RBI → bank → RBI round-trip
# without actually running a Crest agent.
#
# Usage:
#   ./mock-bank-callback.sh RBI-CMS-2026-04-00781 upheld 6100
#   ./mock-bank-callback.sh RBI-CMS-2026-04-00795 partial 590
#   ./mock-bank-callback.sh <reference> <upheld|partial|rejected> <compensation_inr>
# =============================================================================
set -e

REF="${1:-}"
OUTCOME="${2:-upheld}"
COMP="${3:-0}"

if [ -z "$REF" ]; then
    echo "Usage: $0 <RBI-CMS-reference> [outcome] [compensation_inr]"
    echo "Example: $0 RBI-CMS-2026-04-00781 upheld 6100"
    exit 1
fi

RBI_BASE="${RBI_BASE:-http://localhost:8088}"
RBI_TOKEN="${RBI_TOKEN:-rbi_demo_token_change_me}"

# Letter body — pick by outcome and language-aware
case "$OUTCOME" in
    upheld)
        LETTER="Dear Customer,\n\nThank you for raising your concern. The bank has completed its review of complaint reference $REF.\n\nThe bank has determined that your complaint is valid. The disputed amount and associated compensation of Rs $COMP have been credited to your account; these will reflect within 3 working days.\n\nIf you are not fully satisfied with this resolution, you may escalate the matter to our Internal Ombudsman within 30 days. If, after the Internal Ombudsman's review, you remain dissatisfied or do not receive a response within 30 days, you have the right to approach the Reserve Bank Ombudsman under the Reserve Bank — Integrated Ombudsman Scheme 2021, accessible via cms.rbi.org.in.\n\nWarm regards,\nGrievance Cell"
        CITED='[{"source":"RBI","doc":"Master Circular - TAT for Failed Transactions","clause":"ATM auto-reversal T+5; Rs 100/day compensation thereafter","namespace":"rbi-customer-protection"},{"source":"Bank","doc":"Compensation Policy v2.3","clause":"Section 4.2 - ATM compensation","namespace":"bank-grievance-policies"}]'
        ;;
    partial)
        LETTER="Dear Customer,\n\nThank you for raising your concern (reference $REF). The bank has reviewed the matter and the Internal Ombudsman has approved a partial resolution.\n\nAs a service gesture, an amount of Rs $COMP has been credited to your account.\n\nIf you remain dissatisfied, you have the right to approach the Reserve Bank Ombudsman under the Reserve Bank — Integrated Ombudsman Scheme 2021, accessible via cms.rbi.org.in.\n\nWarm regards,\nGrievance Cell"
        CITED='[{"source":"RBI","doc":"Master Circular on Customer Service in Banks","clause":"Cut-off time for same-day credit","namespace":"rbi-customer-protection"}]'
        ;;
    rejected)
        LETTER="Dear Customer,\n\nThank you for raising your concern (reference $REF). The bank, in consultation with the Internal Ombudsman, has reviewed the matter in detail.\n\nThe bank's findings do not support the relief you have requested. The reasoning has been recorded for our records.\n\nIf you remain dissatisfied, you have the right to approach the Reserve Bank Ombudsman under the Reserve Bank — Integrated Ombudsman Scheme 2021 within 30 days, accessible via cms.rbi.org.in.\n\nWarm regards,\nGrievance Cell"
        CITED='[{"source":"Bank","doc":"Customer Service Policy v3.1","clause":"Process review concluded no service deficiency","namespace":"bank-grievance-policies"}]'
        ;;
    *)
        echo "Unknown outcome: $OUTCOME (use upheld | partial | rejected)"
        exit 1
        ;;
esac

TAT_DAYS=$((RANDOM % 14 + 2))
RUN_ID="crest-run-$(date +%s)-$$"

echo "Posting bank callback to $RBI_BASE/api/v1/responses ..."
echo "  reference:      $REF"
echo "  outcome:        $OUTCOME"
echo "  compensation:   Rs $COMP"
echo "  TAT (simulated): $TAT_DAYS days"
echo "  bank_run_id:    $RUN_ID"
echo

curl -s -X POST \
    -H "Authorization: Bearer $RBI_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"complaint_reference_no\": \"$REF\",
        \"bank_code\":         \"HDFC\",
        \"outcome\":           \"$OUTCOME\",
        \"compensation_inr\":  $COMP,
        \"tat_days\":          $TAT_DAYS,
        \"breached_30_day\":   $( [ $TAT_DAYS -gt 30 ] && echo true || echo false ),
        \"customer_letter\":   \"$LETTER\",
        \"cited_clauses\":     $CITED,
        \"bank_run_id\":       \"$RUN_ID\"
    }" \
    "$RBI_BASE/api/v1/responses" \
    | python3 -m json.tool

echo
echo "✓ Done. Reload the complaint detail page to see the bank's response."

#!/usr/bin/env bash
# Create a synthetic phonebook with N contacts for load/performance testing.
# Matches the schema used by integration_tests/suite/test_graphql_load.py.
#
# Usage:
#   TOKEN=... TENANT=... bash contribs/create_synthetic_phonebook.sh
#
# Optional env vars:
#   BASE_URL         (default: https://localhost:9489/0.1)
#   PHONEBOOK_NAME   (default: synthetic-load-test)
#   COUNT            number of contacts to create (default: 25000)
#   BATCH_SIZE       contacts per import request  (default: 5000)
#   NUMBER_BASE      base phone number            (default: 1000000000)
#   MOBILE_BASE      base mobile number           (default: 33600000000)
set -euo pipefail

: "${TOKEN:?Set TOKEN env var to a valid X-Auth-Token}"
: "${TENANT:?Set TENANT env var to a valid Wazo-Tenant UUID}"

BASE_URL="${BASE_URL:-https://localhost:9489/0.1}"
PHONEBOOK_NAME="${PHONEBOOK_NAME:-synthetic-load-test}"
COUNT="${COUNT:-25000}"
BATCH_SIZE="${BATCH_SIZE:-5000}"
NUMBER_BASE="${NUMBER_BASE:-1000000000}"
MOBILE_BASE="${MOBILE_BASE:-33600000000}"

CURL=(curl -sSk -H "X-Auth-Token: $TOKEN" -H "Wazo-Tenant: $TENANT")

die() { echo "ERROR: $*" >&2; exit 1; }

check_error() {
    local response="$1"
    if echo "$response" | jq -e '.message // .error_id' &>/dev/null; then
        echo "$response" | jq . >&2
        die "API error (see above)"
    fi
}

# ── 1. Create phonebook ───────────────────────────────────────────────────────
echo "=== Creating phonebook '$PHONEBOOK_NAME' ==="
RESPONSE=$("${CURL[@]}" -H "Content-Type: application/json" \
    -X POST "$BASE_URL/phonebooks" \
    -d "{\"name\": \"$PHONEBOOK_NAME\", \"description\": \"Synthetic $COUNT-contact phonebook for load testing\"}")
check_error "$RESPONSE"
PB_UUID=$(echo "$RESPONSE" | jq -r '.uuid')
echo "Phonebook UUID: $PB_UUID"

# ── 2. Import contacts in batches ─────────────────────────────────────────────
BATCHES=$(( (COUNT + BATCH_SIZE - 1) / BATCH_SIZE ))
TOTAL_CREATED=0

echo "=== Importing $COUNT contacts in $BATCHES batches of $BATCH_SIZE ==="

for batch in $(seq 1 "$BATCHES"); do
    START=$(( (batch - 1) * BATCH_SIZE ))
    END=$(( batch * BATCH_SIZE - 1 ))
    [ "$END" -ge "$COUNT" ] && END=$(( COUNT - 1 ))

    CSV=$(python3 - "$START" "$END" "$NUMBER_BASE" "$MOBILE_BASE" <<'PY'
import sys
start, end, nb, mb = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
print("firstname,lastname,number,mobile,email")
for i in range(start, end + 1):
    print(f"Contact{i:05d},McContact{i:05d},{nb+i},{mb+i},contact{i:05d}@example.com")
PY
)

    RESPONSE=$(echo "$CSV" | "${CURL[@]}" \
        -H "Content-Type: text/csv; charset=utf-8" \
        -X POST "$BASE_URL/phonebooks/$PB_UUID/contacts/import" \
        --data-binary @-)
    check_error "$RESPONSE"

    CREATED=$(echo "$RESPONSE" | jq '.created | length')
    FAILED_COUNT=$(echo "$RESPONSE" | jq '.failed | length')
    TOTAL_CREATED=$(( TOTAL_CREATED + CREATED ))

    if [ "$FAILED_COUNT" -gt 0 ]; then
        echo "  WARNING: $FAILED_COUNT contacts failed in batch $batch" >&2
        echo "$RESPONSE" | jq '.failed[:3]' >&2
    fi

    echo "  batch $batch/$BATCHES: $CREATED created, $FAILED_COUNT failed ($TOTAL_CREATED/$COUNT total)"
done

# ── 3. Summary ────────────────────────────────────────────────────────────────
cat <<EOF

============================================================
  Done\! $TOTAL_CREATED contacts created.
  Phonebook:  $PHONEBOOK_NAME
  UUID:       $PB_UUID
============================================================

Next steps — create a source pointing at this phonebook:
  PHONEBOOK_UUID=$PB_UUID TOKEN=$TOKEN TENANT=$TENANT \\
    bash contribs/create_phonebook_source.sh
EOF

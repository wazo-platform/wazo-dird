#!/usr/bin/env bash
# Create N phonebook sources pointing at one phonebook, a display, and a
# profile wiring them into the lookup, reverse and favorites services.
# Reproduces the fan-out used by the load tests (one future per source).
#
# Usage:
#   PHONEBOOK_UUID=... TOKEN=... TENANT=... bash contribs/scripts/create_phonebook_source.sh
#
# Required env vars:
#   PHONEBOOK_UUID   uuid of the phonebook to point the sources at
#   TOKEN            a valid X-Auth-Token
#   TENANT           a valid Wazo-Tenant UUID
#
# Optional env vars:
#   BASE_URL         (default: https://localhost:9489/0.1)
#   PROFILE_NAME     (default: default)
#   SOURCE_PREFIX    (default: synthetic-load-test-source)
#   DISPLAY_NAME     (default: synthetic-load-test-display)
#   NUM_SOURCES      number of sources to create (default: 8)
set -euo pipefail

: "${PHONEBOOK_UUID:?Set PHONEBOOK_UUID env var to an existing phonebook UUID}"
: "${TOKEN:?Set TOKEN env var to a valid X-Auth-Token}"
: "${TENANT:?Set TENANT env var to a valid Wazo-Tenant UUID}"

BASE_URL="${BASE_URL:-https://localhost:9489/0.1}"
PROFILE_NAME="${PROFILE_NAME:-default}"
SOURCE_PREFIX="${SOURCE_PREFIX:-synthetic-load-test-source}"
DISPLAY_NAME="${DISPLAY_NAME:-synthetic-load-test-display}"
NUM_SOURCES="${NUM_SOURCES:-8}"

CURL=(curl -sSk -H "X-Auth-Token: $TOKEN" -H "Wazo-Tenant: $TENANT")

die() { echo "ERROR: $*" >&2; exit 1; }

check_error() {
    local response="$1"
    if echo "$response" | jq -e '.message // .error_id' &>/dev/null; then
        echo "$response" | jq . >&2
        die "API error (see above)"
    fi
}

# ── 1. Create sources ─────────────────────────────────────────────────────────
echo "=== Creating $NUM_SOURCES phonebook sources ==="
SOURCE_UUIDS=()
for i in $(seq 1 "$NUM_SOURCES"); do
    RESPONSE=$("${CURL[@]}" -H "Content-Type: application/json" \
        -X POST "$BASE_URL/backends/phonebook/sources" \
        -d "{
            \"name\": \"$SOURCE_PREFIX-$i\",
            \"phonebook_uuid\": \"$PHONEBOOK_UUID\",
            \"searched_columns\": [\"firstname\", \"lastname\", \"number\", \"mobile\", \"email\"],
            \"first_matched_columns\": [\"number\", \"mobile\"],
            \"format_columns\": {\"reverse\": \"{firstname} {lastname}\"}
        }")
    check_error "$RESPONSE"
    UUID=$(echo "$RESPONSE" | jq -r '.uuid')
    SOURCE_UUIDS+=("$UUID")
    echo "  source $i/$NUM_SOURCES: $SOURCE_PREFIX-$i ($UUID)"
done

# JSON array of source identifiers, shared by all three services.
SOURCES_JSON=$(printf '%s\n' "${SOURCE_UUIDS[@]}" | jq -R '{uuid: .}' | jq -s '.')

# ── 2. Create display ─────────────────────────────────────────────────────────
echo "=== Creating display '$DISPLAY_NAME' ==="
RESPONSE=$("${CURL[@]}" -H "Content-Type: application/json" \
    -X POST "$BASE_URL/displays" \
    -d "{
        \"name\": \"$DISPLAY_NAME\",
        \"columns\": [
            {\"title\": \"Firstname\", \"field\": \"firstname\"},
            {\"title\": \"Lastname\", \"field\": \"lastname\"},
            {\"title\": \"Number\", \"field\": \"number\"},
            {\"title\": \"Mobile\", \"field\": \"mobile\"},
            {\"title\": \"Email\", \"field\": \"email\"}
        ]
    }")
check_error "$RESPONSE"
DISPLAY_UUID=$(echo "$RESPONSE" | jq -r '.uuid')
echo "Display UUID: $DISPLAY_UUID"

# ── 3. Create profile ─────────────────────────────────────────────────────────
echo "=== Creating profile '$PROFILE_NAME' ==="
PROFILE_BODY=$(jq -n \
    --arg name "$PROFILE_NAME" \
    --arg display "$DISPLAY_UUID" \
    --argjson sources "$SOURCES_JSON" \
    '{
        name: $name,
        display: {uuid: $display},
        services: {
            lookup: {sources: $sources},
            reverse: {sources: $sources},
            favorites: {sources: $sources}
        }
    }')
RESPONSE=$("${CURL[@]}" -H "Content-Type: application/json" \
    -X POST "$BASE_URL/profiles" -d "$PROFILE_BODY")
check_error "$RESPONSE"
PROFILE_UUID=$(echo "$RESPONSE" | jq -r '.uuid')

cat <<EOF

============================================================
  Done! Profile '$PROFILE_NAME' ($PROFILE_UUID) created with
  $NUM_SOURCES sources wired into lookup, reverse and favorites.
============================================================

Next step — seed favorites for the load test user:
  PROFILE=$PROFILE_NAME TOKEN=$TOKEN TENANT=$TENANT \\
    bash contribs/scripts/create_favorites.sh
EOF

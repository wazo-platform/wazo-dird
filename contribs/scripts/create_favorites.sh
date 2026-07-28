#!/usr/bin/env bash
# Seed favorites for the load-test user so FavoritesUser exercises a real
# fan-out. A single lookup for one synthetic contact returns one result per
# source; each (source, contact) pair is then marked as a favorite, spreading
# favorites across every source in the profile.
#
# Usage:
#   TOKEN=... TENANT=... bash contribs/scripts/create_favorites.sh
#
# Required env vars:
#   TOKEN            a valid X-Auth-Token (favorites are per-user/token)
#   TENANT           a valid Wazo-Tenant UUID
#
# Optional env vars:
#   BASE_URL         (default: https://localhost:9489/0.1)
#   PROFILE          profile to look up and favorite in (default: default)
#   SEARCH_TERM      term matching a synthetic contact   (default: Contact00001)
set -euo pipefail

: "${TOKEN:?Set TOKEN env var to a valid X-Auth-Token}"
: "${TENANT:?Set TENANT env var to a valid Wazo-Tenant UUID}"

BASE_URL="${BASE_URL:-https://localhost:9489/0.1}"
PROFILE="${PROFILE:-default}"
SEARCH_TERM="${SEARCH_TERM:-Contact00001}"

CURL=(curl -sSk -H "X-Auth-Token: $TOKEN" -H "Wazo-Tenant: $TENANT")

die() { echo "ERROR: $*" >&2; exit 1; }

# Fail on any HTTP error status, keeping the response body for diagnostics
# (curl --fail-with-body alone would abort before a captured body is ever
# printed).
curl_or_die() {
    local response rc=0
    response=$("${CURL[@]}" --fail-with-body "$@") || rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "$response" | jq . >&2 2>/dev/null || echo "$response" >&2
        die "curl failed (exit $rc) — see response above"
    fi
    echo "$response"
}

# ── 1. Look up one contact across all sources ─────────────────────────────────
echo "=== Looking up '$SEARCH_TERM' in profile '$PROFILE' ==="
RESPONSE=$(curl_or_die "$BASE_URL/directories/lookup/$PROFILE?term=$SEARCH_TERM")

# Each result carries its source name and the source-specific contact id.
mapfile -t PAIRS < <(
    echo "$RESPONSE" |
        jq -r '.results[] | select(.relations.source_entry_id != null)
               | "\(.source)\t\(.relations.source_entry_id)"' |
        sort -u
)

[ "${#PAIRS[@]}" -gt 0 ] || die "no results with a source_entry_id — is the phonebook populated and the profile wired?"

# ── 2. Mark each (source, contact) as a favorite ──────────────────────────────
# Uses a plain (non-failing) curl call: 409 (already a favorite) is tolerated,
# and any other status only warns rather than aborting the whole batch — both
# would be wrong under curl_or_die.
echo "=== Marking ${#PAIRS[@]} favorites ==="
CREATED=0
for pair in "${PAIRS[@]}"; do
    source="${pair%%$'\t'*}"
    contact="${pair##*$'\t'}"
    status=$("${CURL[@]}" -o /dev/null -w '%{http_code}' \
        -X PUT "$BASE_URL/directories/favorites/$source/$contact")
    case "$status" in
        204) CREATED=$((CREATED + 1)); echo "  favorited: $source/$contact" ;;
        409) echo "  already a favorite: $source/$contact" ;;
        *) echo "  WARNING: PUT $source/$contact returned HTTP $status" >&2 ;;
    esac
done

cat <<EOF

============================================================
  Done! $CREATED favorites created across ${#PAIRS[@]} sources.
============================================================

Run the favorites stress scenario:
  WAZO_LOGIN=... WAZO_PASSWORD=... WAZO_TENANT=$TENANT WAZO_PROFILE=$PROFILE \\
    tox -e load -- FavoritesUser --headless --users 50 --spawn-rate 5 --run-time 60s
EOF

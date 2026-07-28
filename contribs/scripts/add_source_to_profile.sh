#!/usr/bin/env bash
# Append an existing source to a service of an existing profile, in place.
# Unlike create_phonebook_source.sh (which creates a brand-new profile), this
# edits a profile that already exists — e.g. wiring a synthetic phonebook
# source into the stock "default" profile's reverse lookup.
#
# Usage:
#   SOURCE_UUID=... TOKEN=... TENANT=... bash contribs/scripts/add_source_to_profile.sh
#
# Required env vars:
#   SOURCE_UUID      uuid of the source to add
#   TOKEN            a valid X-Auth-Token
#   TENANT           a valid Wazo-Tenant UUID
#
# Optional env vars:
#   BASE_URL         (default: https://localhost:9489/0.1)
#   PROFILE_NAME     profile to edit          (default: default)
#   SERVICE          service to append to     (default: reverse)
set -euo pipefail

: "${SOURCE_UUID:?Set SOURCE_UUID env var to an existing source UUID}"
: "${TOKEN:?Set TOKEN env var to a valid X-Auth-Token}"
: "${TENANT:?Set TENANT env var to a valid Wazo-Tenant UUID}"

BASE_URL="${BASE_URL:-https://localhost:9489/0.1}"
PROFILE_NAME="${PROFILE_NAME:-default}"
SERVICE="${SERVICE:-reverse}"

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

# ── 1. Resolve profile UUID by name ───────────────────────────────────────────
echo "=== Locating profile '$PROFILE_NAME' ==="
PROFILES=$(curl_or_die "$BASE_URL/profiles")
PROFILE_UUID=$(echo "$PROFILES" | jq -r --arg n "$PROFILE_NAME" \
    '.items[] | select(.name == $n) | .uuid' | head -n1)
[ -n "$PROFILE_UUID" ] && [ "$PROFILE_UUID" != "null" ] \
    || die "no profile named '$PROFILE_NAME' in this tenant"
echo "Profile UUID: $PROFILE_UUID"

# ── 2. Append source to the target service (idempotent) ───────────────────────
PROFILE=$(curl_or_die "$BASE_URL/profiles/$PROFILE_UUID")

# Assumes the profile has a display (true for the stock "default" profile).
BODY=$(echo "$PROFILE" | jq \
    --arg src "$SOURCE_UUID" --arg svc "$SERVICE" '
    .display = {uuid: .display.uuid}
    | .services |= with_entries(.value.sources = ((.value.sources // []) | map({uuid: .uuid})))
    | .services[$svc].sources = (
        (.services[$svc].sources // []) as $s
        | if ($s | any(.uuid == $src)) then $s else ($s + [{uuid: $src}]) end
      )
    | {name, display, services}')

echo "=== Adding source $SOURCE_UUID to '$SERVICE' of '$PROFILE_NAME' ==="
curl_or_die -H "Content-Type: application/json" \
    -X PUT "$BASE_URL/profiles/$PROFILE_UUID" -d "$BODY" >/dev/null

COUNT=$(curl_or_die "$BASE_URL/profiles/$PROFILE_UUID" \
    | jq --arg svc "$SERVICE" '.services[$svc].sources | length')

cat <<EOF

============================================================
  Done! '$PROFILE_NAME' now has $COUNT source(s) in '$SERVICE'.
============================================================
EOF

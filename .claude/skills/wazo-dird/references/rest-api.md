# wazo-dird — stable REST + GraphQL API

dird-specific API surface and quirks. General Wazo conventions (`/0.1/` path versioning,
`X-Auth-Token` + `Wazo-Tenant` headers, `message`/`details` error bodies) → `wazo-backend-developer`.
Endpoint paths + behaviors are the stable contract; **exact request/response fields are defined by
each view's `api.yml` (swagger)** — the field lists below are the essentials, not exhaustive nor
guaranteed current. Everything here was exercised against a real stack.

## Reaching a running dird

- **Gateway (use this):** `https://<stack>/api/dird/0.1/…` via nginx. Raw dird port **9489 is NOT
  exposed off-box** — go through the gateway. Self-signed certs → `curl -k`.
- **Token:** admin via `ssh root@<stack> 'wazo-auth-cli token create'` (CLI config lives on the
  stack); **user token** (needed for GraphQL `me` — carries `pbx_user_uuid`) via the auth API:
  ```sh
  curl -sSk -u 'user@domain:password' -X POST https://<stack>/api/auth/0.1/token \
    -H 'Content-Type: application/json' -d '{"expiration":3600,"access_type":"online"}' | jq -r .data.token
  ```
  Introspect: `GET /api/auth/0.1/token/<token>` → `.data.metadata.{tenant_uuid,pbx_user_uuid}`, `.data.acl`.
- **Error shape quirk:** dird's **phonebook** endpoints return `{"reason":[…],"timestamp":[…],
  "status_code":N}` (scalar `status_code`; ≥400 = error) instead of the standard Wazo
  `{"message","details"}` shape. A `check_error` that only greps `.message`/`.error_id` silently
  misses phonebook failures.
- `PUT /profiles/{uuid}` success = **HTTP 204, empty body** — don't treat empty as an error.
- Expired token → small `{"errors":[{"message":"Unauthorized"…}]}` (GraphQL) / 401.

## Stable REST surface (base `/api/dird/0.1`)

- `GET /status`.
- **Phonebooks:** `POST /phonebooks` `{"name","description"}`; `GET /phonebooks`;
  `DELETE /phonebooks/{uuid}` (cascades). Duplicate name → 409 `{"reason":["Duplicating…"]}`.
- **Bulk contact import (seeding fast path):** `POST /phonebooks/{uuid}/contacts/import`,
  `Content-Type: text/csv; charset=utf-8`, body = CSV with header
  (`firstname,lastname,number,mobile,email`). Returns `{"created":[…],"failed":[…]}`; import in
  chunks. Count: `GET /phonebooks/{uuid}/contacts?limit=1` → `.total`. (Seeding recipe: [`tasks.md`](tasks.md).)
- **Sources:** `POST /backends/<backend>/sources`; phonebook source body:
  `{"name","phonebook_uuid","searched_columns":[…],"first_matched_columns":["number","mobile"],
  "format_columns":{"reverse":"{firstname} {lastname}"}}` (`name` is read-only for phonebook
  sources — it mirrors the phonebook's). `wazo` sources: `first_matched_columns` ⊆
  `["exten","mobile_phone_number"]`, else 400. `GET /sources` lists all + their
  `backend` (profile entries store only source `uuid` → resolve here).
- **Displays:** `POST /displays` `{"name","columns":[{"title","field"}]}`.
- **Profiles:** `GET /profiles`, `GET/POST /profiles`, `PUT /profiles/{uuid}`. Body:
  `{"name","display":{"uuid":…},"services":{"lookup":{"sources":[{"uuid":…}]},"reverse":{…},"favorites":{…}}}`.
  Editing an existing profile: GET, transform `display`→`{uuid}` and each service `sources`→`[{uuid}]`,
  append/remove, PUT the FULL body (no partial PUT). POST `default` when it exists → 409.
  Service configs are strictly validated: unknown keys/options → 400; `options.timeout` must be a
  number `> 0`.
- **User-facing directories:** `GET /directories/lookup/<profile>?term=…`,
  `GET /directories/reverse/<profile>/<user_uuid>?exten=…`, `/directories/favorites/...`,
  `/personal` (per-user CRUD).
- **Favorites:** `PUT /directories/favorites/<source>/<contact_id>` — use the
  `relations.source_entry_id` a lookup returned (GraphQL `wazoSourceEntryId`). For `wazo` sources
  that's the confd user **uuid** (the numeric id is still accepted, deprecated, and stored as the
  uuid). Unresolvable id → 400; source unreachable → 503. Deleting a favorite no longer validates
  the id against the source.

## GraphQL reverse lookup

- `POST /graphql`, ACL `dird.graphql.<root_field>` (`dird.graphql.me`). Needs a **user** token.
- ```graphql
  query($profile: String, $extens: [String]) {
    me { contacts(profile: $profile, extens: $extens) {
      edges { node { firstname lastname wazoReverse } } } } }
  ```
  Schema field is `wazo_reverse`; queries use `wazoReverse`.
- **`node: null` for an exten = no match / not resolved in time, NOT an error.** Under load a whole
  request can come back all-null with no `.errors` — that is the reverse timeout, not a failure;
  see [`reverse-lookup.md`](reverse-lookup.md).

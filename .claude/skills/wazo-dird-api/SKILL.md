---
name: wazo-dird-api
description: >-
  Orientation to the wazo-dird directory service — its dird-specific abstractions
  (backend/source, service, profile, display, phonebook, personal), user-facing functionality, and
  the stable REST + GraphQL APIs. Use when working anywhere in wazo-dird: adding or configuring a
  directory source/backend, wiring sources into a profile so users can query them, doing directory
  lookups or GraphQL reverse lookups, managing phonebooks/personal contacts, load- or
  performance-testing dird, or debugging reverse-lookup latency, timeouts, or empty (all-null)
  results. Complements the general `wazo-backend-developer` skill (Wazo service architecture,
  Stevedore/Flask/SQLAlchemy, wdk/tox/alembic workflow, conventions) — this covers only what is
  specific to dird. Detailed references live under `references/` — rest-api.md, reverse-lookup.md,
  dev-and-test.md, tasks.md (see the References section).
---

# wazo-dird — directory service

**Prerequisite:** this assumes the general Wazo backend patterns from the **`wazo-backend-developer`**
skill — standard service layout (`controller.py`/`http_server.py`/`config.py`/`plugins/`/`services/`/
`database/`/`bus.py`), Flask-RESTful + Marshmallow + Stevedore + SQLAlchemy, the wdk/tox/alembic dev
workflow, and conventions (`/0.1/` path versioning, `X-Auth-Token` + `Wazo-Tenant` headers,
AssetLaunchingTestCase integration tests, bus events). Everything below is what's **specific to dird**.

**Mental model:** dird aggregates contacts from many directory *sources* and serves unified
**lookup** (search-as-you-type), **reverse** (exten→name), and **favorites** over a REST +
GraphQL API. Everything is per-**tenant** and selected by a **profile** name the client passes.

## Code structure (dird-specific pieces only)
Standard Wazo service layout (see `wazo-backend-developer`). What's notable in dird:
- `source_manager.py` — instantiates one **source** plugin instance per configured source (an
  extra manager beyond the usual `controller.py`/`plugin_manager.py`).
- `plugins/base_plugins.py` — `BaseSourcePlugin` adds directory methods `search` / `first_match` /
  `match_all` / `list` on top of the generic `load()/unload()`.
- `database/queries/*.py` — one DAO per entity (phonebook, personal, display, profile, source, …);
  `database/models.py` includes the EAV `dird_contact_fields` (name/value/contact_uuid).

## Stevedore plugin extension points (dird-specific)
For how stevedore + setuptools `entry_points` work in general (and `make egg-info`), see
`wazo-backend-developer`. dird exposes **three entry-point groups** — group names / stevedore
namespaces, NOT import paths and NOT API routes — each with a base class in
`plugins/base_plugins.py`. The **authoritative, current** registrations are in `setup.py`'s
`entry_points={…}`; the names below are illustrative examples (they drift — read `setup.py`).
Config gates which registered plugins actually load.

| entry-point group | base class | role | example names (authoritative: `setup.py`) |
|---|---|---|---|
| `wazo_dird.services` | `BaseServicePlugin` | business logic / orchestration | lookup, reverse, favorites, personal, phonebook, profile, display, … |
| `wazo_dird.backends` | `BaseSourcePlugin` | source connectors (implement the directory methods) | wazo, phonebook, personal, ldap, csv, google, office365, conference |
| `wazo_dird.views` | `BaseViewPlugin` | REST/GraphQL endpoints | profiles_view, sources_view, displays_view, graphql_view, `<backend>_backend`, … |

(A backend's *view* — e.g. `phonebook_backend` in `wazo_dird.views` — is the REST surface for
configuring that backend's sources; distinct from the backend in `wazo_dird.backends`.)

## Core abstractions
- **Backend** (`wazo_dird.backends` group): a connector *type* to a data source — `wazo`, `phonebook`,
  `personal`, `conference`, `ldap`, `csv`, `google`, `office365`, … Implements
  `BaseSourcePlugin` (`plugins/base_plugins.py`): roughly `search` → lookup, `first_match` /
  `match_all` → reverse, `list` → favorites/personal (check the base class for the current contract).
- **Source**: a *configured instance* of a backend (name + backend + config + tenant). Created via
  `POST /backends/<backend>/sources`; `source_manager` runs one plugin per source. Wazo
  auto-provisions `auto_*` sources (wazo/conference/google/office365/personal) per tenant.
- **Service** (`wazo_dird.services` group): business logic orchestrating across sources — **lookup**
  (fan out `search`), **reverse** (fan out `first_match`/`match_all`), **favorites**, **personal**
  (per-user contacts), **phonebook** (managed contact collections + CRUD), plus management
  services: display, profile, source, config, cleanup.
- **Display**: ordered column definitions (`title`→`field`) shaping how results are presented.
- **Profile**: the per-tenant object a client queries *by name*. Binds a **display** + a set of
  **sources** to each of lookup / reverse / favorites **services**. "Which sources answer a lookup
  for profile X" == profile X's service→sources mapping.
- **View** (`wazo_dird.views` group): the HTTP/GraphQL surface — REST resources per entity + `/graphql`.

**How a query flows:** client picks a **profile** → the requested **service**
(lookup/reverse/favorites) fans out to that profile's configured **sources** (each a **backend**
instance) → results are shaped by the profile's **display**.

## User-facing functionality (base `/api/dird/0.1`)
- **Lookup:** `GET /directories/lookup/<profile>?term=…`.
- **Reverse:** `GET /directories/reverse/<profile>/<user_uuid>?exten=…`; batched via GraphQL
  `me { contacts(profile, extens) }`.
- **Favorites:** `/directories/favorites/...`.
- **Personal contacts:** `/personal` (per user).
- **Phonebook management:** `/phonebooks` + `/phonebooks/{uuid}/contacts` (+ CSV import).
- **Admin/config:** `/sources`, `/backends/<backend>/sources`, `/displays`, `/profiles`.
- **GraphQL:** `POST /graphql` (reverse lookup for the token's user; ACL `dird.graphql.me`).

## Workflow — make a new directory source usable by users
1. **Create the source** for its backend: `POST /backends/<backend>/sources` with the backend
   config + `searched_columns` (lookup), `first_matched_columns` (reverse), and `format_columns`
   (e.g. `{"reverse":"{firstname} {lastname}"}`). For a phonebook source, create/seed the
   phonebook first and pass its `phonebook_uuid`.
2. **Ensure a display** (`POST /displays`) with the columns clients should see.
3. **Attach to a profile:** GET the target profile (often `default`), add the source `{uuid}` to
   the relevant service(s) (`lookup`/`reverse`/`favorites`), and PUT the **full** profile body
   (partial PUT unsupported; success = 204). The source now answers those services for any client
   on that profile/tenant.
4. **(reverse, large phonebook)** `ANALYZE dird_contact, dird_contact_fields` after bulk import so
   the reverse query plans well (else it can scan/sort the whole phonebook).
5. **Verify:** `GET /directories/lookup/<profile>?term=…` or a GraphQL `me.contacts` reverse.

## dird-specific gotchas
- Reverse `node: null` = no match / timed out, **not** an error; under load the fan-out timeout
  returns all-null. Consider **goodput** (non-null/s), not raw RPS. (→ `reverse-lookup.md`)
- **Phonebook** endpoints error as `{"reason":[…],"status_code":N}` (dird uses this instead of the
  usual Wazo `message`/`details` shape on these routes). (→ `rest-api.md`)
- GraphQL `me` needs a *user* token (with `pbx_user_uuid`), not just any admin token. (→ `rest-api.md`)
- Reverse lookup is a **parallel fan-out with a per-request timeout** across the profile's reverse
  sources, bounded by the `reverse` service's executor pool and the DB pool (sized from
  `rest_api.max_threads`). Exact defaults/config keys: read `reverse_service` + `config.py`.
  (→ `reverse-lookup.md`)
- Tests: `env -u FORCE_COLOR` before `tox`; the integration/explain DB schema is **baked into the
  db image** (a new migration needs `make test-setup` rebuild) while dird app code is mounted live;
  parallel integration/explain runs collide on the fixed docker-compose project name → serialize
  with `flock`. (→ `dev-and-test.md`; general wdk/tox: `wazo-backend-developer`)

## References
Detailed dird-specific companions under `references/` (general Wazo backend patterns →
`wazo-backend-developer`):
- **`rest-api.md`** — stable REST + GraphQL surface: reaching dird (gateway/auth/token), endpoints
  (phonebooks, CSV import, sources, displays, profiles, directories), GraphQL reverse query,
  error-shape quirks.
- **`reverse-lookup.md`** — reverse-lookup internals & tuning: parallel fan-out + timeout,
  executor/DB pools, congestion collapse (goodput vs RPS), phonebook plan-fragility + ANALYZE.
- **`dev-and-test.md`** — dev workflow & test harness: tox envs incl. `explain`/auto_explain,
  db-image schema baking, `flock`/FORCE_COLOR/sandbox gotchas, wdk deploy.
- **`tasks.md`** — task recipes: seed a synthetic phonebook, load-test reverse lookup with `ab`,
  A/B a change on a stack, capture a query's real SQL/plan.

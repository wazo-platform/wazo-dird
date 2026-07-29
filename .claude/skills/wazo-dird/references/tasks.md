# wazo-dird — task recipes & tips

Concrete recipes for common dird testing/ops tasks. API details → `rest-api.md`; interpreting
reverse-lookup results → `reverse-lookup.md`; test harness → `dev-and-test.md`.

## Seed a synthetic phonebook (for load/perf testing)
Against a running stack, create a phonebook and bulk-import contacts via the CSV endpoint
(`rest-api.md`), in batches (a few thousand per request). Sequential integer numbers/mobiles make
reverse-lookup extens predictable (pick a base like `1000000000`). Make it idempotent: on create,
treat the duplicate-name error as "reuse" (look it up in `GET /phonebooks` by name); skip import if
the contact count is already at the target. Then wire a phonebook **source** at it and add that
source to a profile's `reverse` service (SKILL.md workflow). After a large import,
`ANALYZE dird_contact, dird_contact_fields` (see `reverse-lookup.md`).

## Load-test reverse lookup with `ab`
Build a GraphQL body file (`rest-api.md` query) and POST it:
```sh
ab -n <N> -c <C> -k -p body.json -T 'application/json' \
   -H "X-Auth-Token: $TOKEN" -H "Wazo-Tenant: $TENANT" \
   https://<stack>/api/dird/0.1/graphql
```
- `ab` supports HTTPS. Use a **user** token (GraphQL `me`); refresh it before a multi-minute run
  (tokens expire — an expired one turns every response into a small `Unauthorized` body).
- **Interpreting output:** ab's **"Failed (Length)"** counts responses whose body length differs
  from the first. For a *fixed* reverse query that means **all-null (empty) results** (the reverse
  timeout, `reverse-lookup.md`), NOT HTTP errors. Cross-check by firing a concurrent `curl` sample
  and parsing `.data.me.contacts.edges` for null nodes.
- **Method:** keep `-n` **fixed** across concurrency levels (varying it with `-c` makes levels
  incomparable). Report **goodput** (non-null responses/s) and p50/p95, not raw RPS. Keep the full
  ab output (tee to a file). Give the stack to yourself — a co-tenant load test or heavy local
  docker build starves the `ab` client and produces phantom non-2xx/latency swings.

## A/B a reverse-lookup change on a real stack
Run the same `ab` scenarios against the **unmounted release** (baseline) and the **mounted branch**
(`wdk mount -r wazo-dird`), same fixed `-n`/`-c`, same profile, quiet stack. Compare goodput +
p50/p95; 0 failures on both = no functional regression. For non-phonebook reverse (no phonebook
source in the profile), expect near-parity if the change only touches phonebook/personal code —
confirm which code paths the change actually affects.

## Inspect the actual SQL a query generates
Two options: run under `tox -e explain` (auto_explain captures EXPLAIN ANALYZE for every query — see
`dev-and-test.md`); or, in a test, hook SQLAlchemy's `before_cursor_execute` to capture the exact
emitted statement, then run `EXPLAIN (ANALYZE, FORMAT JSON)` on it and assert on the plan (e.g. no
Sort/Hash over a large row count, or that a specific index is used). The latter is a good pattern
for a deterministic plan-stability guard in the performance suite.

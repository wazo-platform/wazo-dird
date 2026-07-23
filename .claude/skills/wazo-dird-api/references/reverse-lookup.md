# wazo-dird — reverse-lookup internals & tuning

How reverse lookup behaves under load, why it returns empty results, and the knobs that control it.
Read this when debugging slow/empty reverse lookups or sizing a deployment. Concrete values
(timeout default, pool defaults, config keys) change — this says *where* they live; read the code
to confirm. (Request/response shape → `rest-api.md`; load-testing → `tasks.md`.)

## Fan-out model
- A reverse request **fans out to the profile's `reverse`-service sources in parallel** — one task
  per source on the reverse service's `ThreadPoolExecutor` — and collects results until every
  requested exten resolves or a per-request timeout fires. See
  `wazo_dird/plugins/reverse_service/plugin.py`.
- On timeout it cancels the still-pending source tasks and returns whatever resolved (**partial /
  all-null**). So contention surfaces as *empty results* (`node: null`), not errors or merely slow
  responses. The timeout's default and its per-profile config key are in that plugin — check it.

## Pools
- `rest_api.max_threads` bounds WSGI request concurrency and also sizes the SQLAlchemy connection
  pool (the DB pool is derived from it in `database/helpers.py` / `controller.py`).
- Each service has an `executor_workers` setting (`lookup`/`reverse`/`favorites`); unset ⇒ it falls
  back to `rest_api.max_threads`. Defaults live in `config.py`; deployments override in
  `/etc/wazo-dird/conf.d/*.yml`. Read those for actual values.

## Congestion collapse
- Concurrency × sources-per-profile source tasks compete for the executor + DB pools; past capacity,
  requests queue past the timeout → high empty-rate + high p50.
- **Measure goodput (non-null responses/s), not raw RPS.** Raw RPS counts all-null timeouts as
  successes and hides the collapse (RPS can *rise* while useful work craters).

## Latency sources to control for
- **External sources** dominate fan-out latency and variance: google/office365 make live HTTP
  calls, wazo/conference hit confd. A mis-configured/disabled external source can make the whole
  fan-out time out until it's removed from the profile. Isolate DB-query-cost measurements from
  these (e.g. a phonebook-only or personal-only profile).

## Phonebook reverse query can be plan-fragile on large phonebooks
- The phonebook backend's batched reverse query (see `database/queries/phonebook.py`) is sensitive
  to Postgres planner statistics. Observed failure mode: with **stale `dird_contact` statistics**
  (e.g. right after a bulk import, before autovacuum/ANALYZE), the planner mis-estimates the
  phonebook join and materializes the whole phonebook (Sort/Hash, O(phonebook size), independent of
  exten count) instead of index-probing the matched contacts; on a warm/ANALYZEd DB the same query
  plans fine. Confirm the current query shape and any indexes in the code before assuming a plan.
- Mitigations that helped in testing (verify which, if any, are in the current code):
  1. `ANALYZE dird_contact, dird_contact_fields` after a bulk import — statistics currency was the
     decisive factor;
  2. a composite index over the matched columns on `dird_contact_fields`;
  3. rewriting the phonebook/tenant scoping so the planner drives from the selective exten
     predicate.
  In experiments the query-form changes (2)+(3) alone did not fix the multi-exten case under stale
  stats — (1) did.
- `dird_contact_fields` stores contact attributes EAV-style (a row per field). Check
  `database/models.py` for the current columns/indexes.

## How to see the real plan
Use `tox -e explain` (auto_explain) or capture the emitted SQL in a test and `EXPLAIN (ANALYZE,
FORMAT JSON)` it — see `dev-and-test.md` and `tasks.md`.

# wazo-dird — dev workflow & test harness

dird-specific dev/test details. General wdk (mount/restart/tailf), tox (`py311`/`linters`/
`integration`), and alembic usage → the `wazo-backend-developer` skill. Paths/targets/env names
below can change — treat them as *where to look*, and confirm in `tox.ini` / `Makefile` /
`integration_tests/`.

## Test environments (tox)
- Usual envs: unit (`py311`), `linters` (pre-commit: flake8/black/mypy/isort/…), `integration`
  (Docker Compose under `integration_tests/suite/`). Definition of done: linters + mypy green, type
  hints on new public functions, tests for new behavior.
- **`tox -e explain`** (dird-specific) — runs the performance suite with Postgres **`auto_explain`**
  enabled via a compose override, logging EXPLAIN ANALYZE for **every** query to a per-run dir under
  `integration_tests/explain-logs/` (can be very large — grep for the query of interest rather than
  reading whole). Use it to see the real ORM-emitted SQL + plan. Check `tox.ini` for the exact env
  definition and which suite/override it wires.
- Heavier load/perf tests live under `integration_tests/performance_suite/` and are not run by the
  default integration env.

## Gotchas that waste runs
- **`env -u FORCE_COLOR` before `tox`** — a non-bool `FORCE_COLOR` (e.g. `3`) crashes tox's arg parser.
- The integration harness (via `wazo_test_helpers`) names each Compose project after the asset, so
  two runs of the **same asset** collide on container names (host ports are dynamic and don't
  clash). Serialize the docker phase with `flock <lockfile> <tox cmd>` when running parallel
  worktrees.
- The integration **DB image's schema is built by running the alembic migrations at image-build
  time** (see the db image's Dockerfile under `contribs/docker/`), so a **new migration only takes
  effect after the db image is rebuilt** (`make test-setup` / the db-image build target). The dird
  **app code is bind-mounted** into the container (see the compose file), so pure-Python changes
  apply on restart without a rebuild. Verify both mechanisms in the current compose/Makefile.
- `make egg-info` after adding/removing plugins (regenerates stevedore entry points).

## Deploying to a real stack (wdk)
- `wdk mount -r wazo-dird` rsyncs local code to the stack and restarts dird (mounted → Python edits
  apply); `wdk umount wazo-dird` reverts to the installed `.deb` (restart dird after); `wdk mount
  --list` shows state; config in `~/.config/wdk/config.yml`.
- Mounting a branch vs. running the installed `.deb` is a handy **A/B baseline** for behavior/perf
  changes. Note the installed release can lag the branch (e.g. a backend method the branch adds may
  be absent in the release) — check the deployed version rather than assuming parity.
- **Stack traffic runs outside the command sandbox** (stack host not whitelisted) — disable the
  sandbox for curl/ssh/docker against a stack. Auth token: see `rest-api.md`.

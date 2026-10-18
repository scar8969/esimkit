# Changelog

All notable changes to esimkit are documented here.

The format follows Keep a Changelog (https://keepachangelog.com/en/1.1.0/), and
this project adheres to Semantic Versioning
(https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Recorded quality-gate evidence, quoted verbatim in
  [docs/EVIDENCE.md](docs/EVIDENCE.md) and in the README: 135 tests passed with 0
  failures and 0 warnings, and 100.00% coverage of 693 statements, alongside the
  exact commands that produced both.
- Strict type annotations across all 15 source modules, so `mypy` reports no
  issues and `pyflakes` reports no findings. The suite went from 73 type errors in
  9 files to zero.
- Dependency-free SVG charts of test, coverage, latency, payload, LOC and
  file-count data under `docs/assets/`, generated from the recorded metrics
  document and committed so they render on the repository page without a build
  step.
- Eleven test modules covering the LPA JSON API, the daemon bridge, the SM-DP+
  helper, the error table, runtime paths, observability, the HTTP internals, the
  application factory, the pages and the CLI. The suite grew from 24 tests to 135.
- The OpenAPI document now declares `/api/health`, which the application served
  but never documented, and its duplicate `/api/profiles` key is merged into one
  path with both operations.

### Changed

- Every `Query.get_or_404()` call became `db.get_or_404()`, removing the
  SQLAlchemy 2.0 legacy deprecation warnings from the suite.
- `datetime.utcnow()` is deprecated since 3.12 and warns on every call; the
  naive-UTC helper is now built from an aware `datetime.now(UTC)`. (It has not
  been removed in 3.14 - that removal is still only planned.)
- The development-server block (`if __name__ == "__main__"`) moved out of the
  application factory, where it could never be reached from an import and could
  never be covered, to the module level where the guard means something.
- `docs/OPERATIONS.md` and the ADR now describe the metrics that are actually
  exported: `http_requests_total{method,status}` and
  `http_request_duration_seconds_sum{method}`, with no histogram, no count and no
  p99.

### Fixed

- `POST /api/profiles` and `POST /api/discover` answered `500` when the JSON body
  was an array or a string. `(request.get_json() or {}).get(...)` does not protect
  against a non-empty list, because a list is truthy, so `.get` was called on the
  wrong type and raised `AttributeError`. Both now answer the field-level `400`.
- `POST /api/discover` passed the address straight to `smdp.resolve()`, which
  raises `ValueError` for anything that is not an LPA activation code; a malformed
  or missing address therefore produced a `500` after a full traceback. It is now
  a typed `BadRequest` and a `400`.
- `POST /api/profiles` indexed the bridge payload with `prof["iccid"]`, so a bridge
  that answered without one raised `KeyError` and produced a `500`. A broken
  dependency is now a `ServiceUnavailable` and a `503`, which is what it is.
- The HTML install form and `cli install` had the same unguarded `iccid` access;
  the form now flashes and redirects, and the CLI exits 2 with a message.
- `cli._db()` leaked one application context and one SQLAlchemy engine per
  invocation; it now disposes the engine, pops it from the registry and pops the
  context.
- Overrides prefixed `EASYLPAC_` were ignored: `paths.ENV_PREFIX` was missing its
  trailing underscore, so the namespaced lookup asked for the unreachable
  `EASYLPACDATA_DIR`.

### Known limitations

- The hardware path is simulated, and the README says so. `smdp.download_via_es10b()`
  returns a hard-coded ICCID and a carrier derived from the server name, and
  `LpaBridge.get_eid()` answers `"8904-MOCK-EID"` when `lpacd` is not on `PATH`.
  Nothing here has ever touched an eUICC or a modem.
- No screenshot is committed, because no headless browser can start on the host
  that produced this release: Chrome, Edge and the Playwright bundle all fail on an
  operating-system access denial. The HTTP surface is evidenced with recorded
  status codes, sizes and bodies instead.
- `ruff`, `bandit` and `pip-audit` are configured but were never executed here: the
  generating host has no network access. `pyflakes` and `mypy` are the static
  checks that could run, and both are clean.
- No container image has been built.

## [0.1.0] - 2026-10-08

First release under the current packaging. This is the industry-baseline
release: the domain behaviour is the original contract's, and everything around
it is new.

### Added

- `src/` layout with an installable distribution and a typed, importable
  package (`pip install -e .`).
- `create_app()` application factory plus a compatibility `wsgi.py` shim.
- Environment-driven configuration parsed into a frozen `Settings` object and
  validated at startup with actionable errors.
- Structured JSON logging with per-request correlation ids.
- Operational endpoints: `/healthz`, `/livez`, `/readyz`, `/metrics`
  and `/version`.
- Security headers and a uniform JSON error envelope on every response.
- Hand-rolled Prometheus text exposition, with no `prometheus_client`
  dependency.
- Multi-stage Dockerfile running as an unprivileged user, with a healthcheck, a
  read-only root filesystem and dropped capabilities.
- `Makefile`, pre-commit configuration, ruff and mypy configuration, pytest
  with a coverage floor, and a GitHub Actions pipeline covering lint, type, test,
  security and container build.
- Documentation set: README, architecture, operations runbook, ADRs, security
  policy, contributing guide and this changelog.

### Changed

- Every historical flat import was rewritten to a package-relative import, so the
  modules can no longer be shadowed.
- Runtime state moved to `var/` (database, logs), outside the importable tree.

### Known limitations

- ruff, bandit and pip-audit are configured but were never executed: the
  generating sandbox had no network access.
- The coverage floor is configured here; it was measured in the following pass
  at 100.00%, above the 85% gate.
- No container image has been built.

[Unreleased]: https://example.invalid/easylpac/compare/v0.1.0...HEAD
[0.1.0]: https://example.invalid/easylpac/releases/tag/v0.1.0

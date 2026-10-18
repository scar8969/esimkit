"""HTTP plumbing contract: metrics, ops-path adoption, method guards.

Each case builds a fresh Flask application, because Flask refuses to register a
rule or blueprint once an application has handled its first request.
"""

from __future__ import annotations

import pytest
from flask import Flask

from easylpac import http, observability
from easylpac.config import Settings


@pytest.fixture()
def bare_settings():
    return Settings.from_env({"APP_ENV": "test", "SECRET_KEY": "test-secret", "LOG_JSON": "1"})


def test_counter_increments_accumulates_and_resets():
    counter = http.Counter()
    counter.inc("demo", value=2, status="200")
    counter.inc("demo", value=3, status="200")
    assert counter.snapshot() == [("demo", {"status": "200"}, 5.0)]
    counter.reset()
    assert counter.snapshot() == []


def test_metrics_renders_type_once_and_handles_labels(monkeypatch):
    counter = http.Counter()
    monkeypatch.setattr(http, "METRICS", counter)
    counter.inc("demo_total", value=2, status="200")
    counter.inc("demo_total", value=3, status="404")
    counter.inc("plain_total")
    counter.inc("weird name!")

    text = http.render_metrics()

    assert text.count("# TYPE demo_total counter") == 1
    assert 'demo_total{status="200"} 2' in text
    assert 'demo_total{status="404"} 3' in text
    assert "plain_total 1" in text
    assert "weird_name_ 1" in text
    assert "# TYPE process_uptime_seconds gauge" in text


def test_production_responses_carry_hsts():
    app = Flask(__name__)

    @app.get("/ping")
    def ping():
        return "pong"

    production = Settings.from_env({"APP_ENV": "production", "SECRET_KEY": "s"})
    http.install_observability(app, production)
    with app.test_client() as client:
        response = client.get("/ping")
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")


def test_an_unhandled_exception_is_logged_at_teardown(monkeypatch, bare_settings):
    records = []

    class Recorder:
        def info(self, *args, **kwargs):
            records.append(("info", args, kwargs))

        def exception(self, *args, **kwargs):
            records.append(("exception", args, kwargs))

    recorder = Recorder()
    real = observability.get_logger
    monkeypatch.setattr(
        observability,
        "get_logger",
        lambda name: recorder if name == "easylpac.error" else real(name),
    )

    app = Flask(__name__)

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    http.install_observability(app, bare_settings)
    app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
    with app.test_client() as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert any(kind == "exception" for kind, _args, _kwargs in records)


def test_adopt_ops_paths_merges_a_legacy_dict_payload(bare_settings):
    app = Flask(__name__)

    @app.get("/healthz")
    def legacy_health():
        return {"legacy": True}

    assert http.adopt_ops_paths(app, bare_settings, ()) == ["/healthz"]
    with app.test_client() as client:
        body = client.get("/healthz").get_json()
    assert body["legacy"] is True
    assert body["status"] == "ok"
    assert body["service"] == "easylpac"


def test_adopt_ops_paths_merges_a_legacy_tuple_payload(bare_settings):
    app = Flask(__name__)

    @app.get("/livez")
    def legacy_live():
        return {"legacy": "live"}, 201

    http.adopt_ops_paths(app, bare_settings, ())
    with app.test_client() as client:
        response = client.get("/livez")
    assert response.status_code == 200
    assert response.get_json()["legacy"] == "live"
    assert response.get_json()["status"] == "alive"


def test_adopt_ops_paths_keeps_a_non_json_legacy_response(bare_settings):
    app = Flask(__name__)

    @app.get("/readyz")
    def legacy_ready():
        return "legacy page"

    http.adopt_ops_paths(app, bare_settings, ())
    with app.test_client() as client:
        response = client.get("/readyz")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "legacy page"


def test_guard_ops_methods_refuses_writes_on_read_only_paths():
    app = Flask(__name__)

    @app.get("/healthz")
    def legacy_health():
        return {"status": "ok"}

    assert http.guard_ops_methods(app, ["/healthz"]) == ["/healthz"]
    with app.test_client() as client:
        assert client.post("/healthz").status_code == 405
        assert client.get("/healthz").status_code == 200


def test_guard_ops_methods_skips_a_path_that_publishes_every_method():
    app = Flask(__name__)

    @app.route("/healthz", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def legacy_health():
        return "ok"

    assert http.guard_ops_methods(app, ["/healthz"]) == []


def test_guard_ops_methods_is_idempotent():
    app = Flask(__name__)

    @app.get("/healthz")
    def legacy_health():
        return "ok"

    assert http.guard_ops_methods(app, ["/healthz"]) == ["/healthz"]
    assert http.guard_ops_methods(app, ["/healthz"]) == []


def test_guard_ops_methods_does_not_clobber_an_existing_endpoint():
    app = Flask(__name__)

    @app.get("/healthz")
    def legacy_health():
        return "ok"

    app.view_functions["_ops_method_guard__healthz"] = lambda: "reserved"
    assert http.guard_ops_methods(app, ["/healthz"]) == []


def test_ops_blueprint_honours_the_skip_list(bare_settings):
    blueprint = http.ops_blueprint(bare_settings, skip={"/healthz"})
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/healthz" not in rules
    assert {"/livez", "/readyz", "/metrics", "/version"} <= rules


def test_readyz_reports_every_failing_check(bare_settings):
    def missing_dependency():
        return False

    def broken_check():
        raise RuntimeError("no db")

    def warned():
        return {"ok": False, "error": "degraded"}

    blueprint = http.ops_blueprint(
        bare_settings, readiness_checks=[missing_dependency, broken_check, warned]
    )
    app = Flask(__name__)
    app.register_blueprint(blueprint)
    with app.test_client() as client:
        response = client.get("/readyz")
    assert response.status_code == 503
    failures = {f["check"]: f["error"] for f in response.get_json()["failures"]}
    assert failures["missing_dependency"] == "returned False"
    assert failures["broken_check"].startswith("RuntimeError: no db")
    assert failures["warned"] == "degraded"

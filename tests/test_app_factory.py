"""Application factory contract: settings plumbing and the WSGI singleton."""

from __future__ import annotations

from flask import Flask

import easylpac.app as app_module
from easylpac.config import Settings


def test_legacy_config_forwards_the_database_uri_when_supplied():
    settings = Settings.from_env({"DATABASE_URL": "sqlite:///tmp/example.db"})
    config = app_module._legacy_config(settings)
    assert config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///tmp/example.db"
    assert config["MAX_CONTENT_LENGTH"] == settings.max_content_length
    assert config["SQLALCHEMY_TRACK_MODIFICATIONS"] is False


def test_legacy_config_omits_an_unset_database_uri():
    config = app_module._legacy_config(Settings.from_env({}))
    assert "SQLALCHEMY_DATABASE_URI" not in config


def test_load_legacy_app_with_no_config_returns_the_shared_application():
    assert isinstance(app_module._load_legacy_app({}), Flask)


def test_readiness_checks_start_empty():
    assert tuple(app_module.readiness_checks()) == ()


def test_get_app_builds_and_caches_the_singleton():
    app_module._APP = None
    first = app_module.get_app()
    assert isinstance(first, Flask)
    assert app_module.get_app() is first

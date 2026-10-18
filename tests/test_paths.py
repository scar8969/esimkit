"""Filesystem layout contract: prefixed/bare overrides and derived dirs.

The prefixed spelling is the one an operator would guess from the variable
names, so it must win; the bare name remains a supported fallback.
"""

from __future__ import annotations

import pathlib

from easylpac import paths


def test_env_prefix_ends_in_the_separator():
    # Regression: ENV_PREFIX was "EASYLPAC" without the trailing underscore, so
    # every EASYLPAC_<NAME> override was silently ignored and the bare name won.
    assert paths.ENV_PREFIX == "EASYLPAC_"


def test_paths_accept_the_prefixed_spelling_first(monkeypatch, tmp_path):
    monkeypatch.setenv("EASYLPAC_DATA_DIR", str(tmp_path / "prefixed"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "bare"))

    assert paths._env_path("DATA_DIR", tmp_path) == tmp_path / "prefixed"


def test_a_prefixed_override_is_honoured(monkeypatch, tmp_path):
    monkeypatch.setenv("EASYLPAC_LOG_DIR", str(tmp_path / "logs"))

    assert paths._env_path("LOG_DIR", tmp_path) == tmp_path / "logs"


def test_paths_expand_a_user_home_in_the_supplied_value(monkeypatch, tmp_path):
    monkeypatch.setenv("EASYLPAC_LOG_DIR", "~/easylpac-logs")

    assert paths._env_path("LOG_DIR", tmp_path) == pathlib.Path("~/easylpac-logs").expanduser()


def test_paths_fall_back_to_the_bare_spelling(monkeypatch, tmp_path):
    monkeypatch.delenv("EASYLPAC_INSTANCE_DIR", raising=False)
    monkeypatch.setenv("INSTANCE_DIR", str(tmp_path / "bare"))

    assert paths._env_path("INSTANCE_DIR", tmp_path) == tmp_path / "bare"


def test_paths_fall_back_to_the_supplied_default(monkeypatch):
    monkeypatch.delenv("EASYLPAC_LOG_DIR", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)

    assert paths._env_path("LOG_DIR", paths.DATA_DIR / "log") == paths.DATA_DIR / "log"


def test_log_dir_defaults_under_the_data_dir(monkeypatch):
    monkeypatch.delenv("EASYLPAC_LOG_DIR", raising=False)
    monkeypatch.delenv("LOG_DIR", raising=False)

    assert paths.LOG_DIR == paths.DATA_DIR / "log"


def test_the_runtime_layout_is_derived_from_the_package_location():
    rendered = paths.as_dict()
    assert rendered["package_dir"] == str(paths.PACKAGE_DIR)
    assert rendered["templates_dir"] == str(paths.TEMPLATES_DIR)
    assert rendered["instance_dir"] == str(paths.INSTANCE_DIR)
    assert paths.PACKAGE_DIR.parent == paths.SRC_DIR
    assert paths.SRC_DIR.parent == paths.PROJECT_ROOT


def test_ensure_runtime_dirs_is_idempotent():
    paths.ensure_runtime_dirs()
    paths.ensure_runtime_dirs()
    assert paths.INSTANCE_DIR.is_dir()
    assert paths.LOG_DIR.is_dir()

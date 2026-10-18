"""Pytest bootstrap for the easylpac test suite.

The distribution uses a src/ layout, so a fresh checkout is not importable
until it is installed. Adding src/ to sys.path here means pytest works straight
from the repository, whether or not the package has been installed.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# The suite must never write to the repository's var/ directory. easylpac.paths
# derives its layout from the environment at import time, so a throwaway root is
# installed *before* the package is first imported. DATA_DIR is the documented
# variable; INSTANCE_DIR and LOG_DIR are derived from it, which also exercises
# the fallback branch in paths._env_path.
_RUNTIME_DIR: str | None = None
if not os.environ.get("EASYLPAC_DATA_DIR") and not os.environ.get("DATA_DIR"):
    _RUNTIME_DIR = tempfile.mkdtemp(prefix="easylpac-tests-")
    os.environ["EASYLPAC_DATA_DIR"] = _RUNTIME_DIR

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def discard_runtime_dir():
    """Remove the throwaway runtime root once the session is over."""
    yield
    if _RUNTIME_DIR is not None:
        shutil.rmtree(_RUNTIME_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def settings():
    """Deterministic settings for the whole session."""
    from easylpac.config import Settings, reset_settings

    reset_settings()
    return Settings.from_env(
        {
            "APP_ENV": "test",
            "SECRET_KEY": "test-secret-key",
            # INFO, not WARNING: the access-log contract test asserts the
            # structured line is actually emitted, and the root handler
            # honours this level.
            "LOG_LEVEL": "INFO",
            "LOG_JSON": "1",
        }
    )


@pytest.fixture()
def client(settings):
    """Flask test client bound to the factory-built application."""
    from easylpac.app import create_app

    app = create_app(settings)
    app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    with app.test_client() as test_client:
        yield test_client

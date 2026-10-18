"""Model defaults: naive-UTC timestamps without the deprecated utcnow().

datetime.utcnow() is deprecated since 3.12 and warns on every call; the default
is now built from an aware now(UTC) and stripped back to naive.
"""

from __future__ import annotations

from datetime import UTC, datetime

from easylpac import models
from easylpac.models import Notification, Profile, db


def test_utcnow_returns_a_naive_utc_timestamp():
    stamp = models._utcnow()
    assert stamp.tzinfo is None
    assert abs((datetime.now(UTC).replace(tzinfo=None) - stamp).total_seconds()) < 5


def test_the_column_defaults_are_the_naive_utc_helper():
    # Regression: both columns defaulted to datetime.utcnow, which is deprecated
    # since 3.12 and warns on every insert. SQLAlchemy wraps the default as a
    # context-taking callable, but it keeps the function's name, so the name
    # distinguishes the aware-then-stripped helper from utcnow.
    for column in (Profile.__table__.c.installed_at, Notification.__table__.c.at):
        assert getattr(column.default.arg, "__name__", "") == "_utcnow"
        assert not hasattr(column.default.arg, "__self__")


def test_inserting_a_profile_stamps_installed_at():
    db.session.add(Profile(iccid="8914"))
    db.session.commit()
    row = db.session.get(Profile, "8914")
    assert row.installed_at is not None
    assert row.installed_at.tzinfo is None

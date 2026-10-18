from datetime import UTC, datetime
from typing import Any

from flask_sqlalchemy import SQLAlchemy

# flask_sqlalchemy builds the declarative base lazily inside init_app and stores
# it as an instance attribute, so db.Model is invisible to a static checker and
# every db.Column below would be flagged. Binding it once, to a plainly
# Any-typed alias, keeps the rest of the module checkable; the easylpac.models
# override in mypy.ini turns off disallow_subclassing_any for this module
# because the base genuinely is dynamic.
db = SQLAlchemy()
Base: Any = db.Model


def _utcnow() -> datetime:
    """Naive UTC timestamp, matching the naive DateTime columns below.

    ``datetime.utcnow()`` is deprecated since 3.12 and raises a
    ``DeprecationWarning`` on every call (verified on the 3.14 interpreter that
    runs this suite), so the default is built from an aware ``now(UTC)`` and
    stripped back to naive.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class Profile(Base):
    __tablename__ = "profiles"
    iccid = db.Column(db.String(32), primary_key=True)
    eid = db.Column(db.String(32), default="")
    carrier = db.Column(db.String(64), default="")
    state = db.Column(db.String(16), default="installed")  # installed|enabled|disabled|deleted
    smdp = db.Column(db.String(128), default="")
    installed_at = db.Column(db.DateTime, default=_utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    profile_iccid = db.Column(db.String(32), db.ForeignKey("profiles.iccid"))
    kind = db.Column(db.String(16), default="")
    message = db.Column(db.String(256), default="")
    at = db.Column(db.DateTime, default=_utcnow)

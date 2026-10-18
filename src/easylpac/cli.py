"""lpac - EasyLPAC command line (mirrors lpa/api.py).

Exit codes: 0 success, 2 refused (bad input, illegal transition, or no hardware
bridge).  The bridge itself is never stubbed: without lpacd the command reports
the same degradation the HTTP API returns as 503.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from . import paths
from .lpa.bridge import LpaBridge
from .lpa.profiles import can_transition
from .lpa.smdp import resolve


@contextmanager
def _db() -> Iterator[Any]:
    """Open a throwaway application context against the real schema.

    The CLI is usually one process per invocation, but tests call several
    commands in a single interpreter. A fresh Flask app per invocation would
    otherwise leave its engine and its application context alive in the
    process-wide state Flask-SQLAlchemy keeps, so both are torn down on exit.
    """
    from flask import Flask

    from .models import db

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "easylpac.db")
    db.init_app(app)
    ctx = app.app_context()
    ctx.push()
    try:
        db.create_all()
        yield db
    finally:
        db.session.remove()
        for engine in (db._app_engines.pop(app, None) or {}).values():
            engine.dispose()
        ctx.pop()


def _bridge() -> LpaBridge:
    return LpaBridge()


def cmd_list(_args: argparse.Namespace) -> int:
    from .models import Profile

    with _db():
        rows = Profile.query.order_by(Profile.iccid).all()
        if not rows:
            print("no profiles installed")
            return 0
        for p in rows:
            print(f"{p.iccid:<22} {p.carrier:<16} {p.state:<10} {p.smdp}")
        return 0


def cmd_install(args: argparse.Namespace) -> int:
    bridge = _bridge()
    try:
        server = resolve(args.activation_code)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"SM-DP+ {server}")
    try:
        prof = bridge.install(args.activation_code)
    except NotImplementedError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    iccid = prof.get("iccid")
    if not iccid:
        print("refused: bridge returned no iccid", file=sys.stderr)
        return 2
    from .models import Profile

    with _db() as db:
        p = Profile(iccid=iccid, eid=prof.get("eid", ""), carrier=prof.get("carrier", ""),
                    state="installed", smdp=prof.get("smdp", server))
        db.session.merge(p)
        db.session.commit()
        print(f"installed {p.iccid} ({p.carrier})")
        return 0


def cmd_enable(args: argparse.Namespace) -> int:
    from .models import Profile

    with _db() as db:
        p = Profile.query.filter_by(iccid=args.iccid).first()
        if p is None:
            print(f"error: no profile {args.iccid}", file=sys.stderr)
            return 2
        if not can_transition(p.state, "enabled"):
            print(f"error: cannot enable from {p.state}", file=sys.stderr)
            return 2
        try:
            _bridge().enable(args.iccid)
        except NotImplementedError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        p.state = "enabled"
        db.session.commit()
        print(f"enabled {p.iccid}")
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lpac")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list", help="list installed profiles")
    inst = sub.add_parser("install", help="install a profile from an activation code")
    inst.add_argument("activation_code")
    en = sub.add_parser("enable", help="enable an installed profile")
    en.add_argument("iccid")
    args = p.parse_args(argv)
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "install":
        return cmd_install(args)
    if args.cmd == "enable":
        return cmd_enable(args)
    p.print_help()
    return 1

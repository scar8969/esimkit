"""lpac — EasyLPAC command line (mirrors lpa/api.py).

Exit codes: 0 success, 2 refused (bad input, illegal transition, or no hardware
bridge).  The bridge itself is never stubbed: without lpacd the command reports
the same degradation the HTTP API returns as 503.
"""
from .lpa.profiles import can_transition
from .lpa.smdp import resolve

import argparse, sys
from . import paths

def _db():
    """Open the SQLite session lazily so `--help` needs no Flask-SQLAlchemy."""
    from flask import Flask
    from .models import db
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "easylpac.db")
    db.init_app(app)
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    return db

def _bridge():
    from .lpa.bridge import LpaBridge
    return LpaBridge()

def cmd_list(_args):
    from .models import Profile
    db = _db()
    rows = Profile.query.order_by(Profile.iccid).all()
    if not rows:
        print("no profiles installed")
        return 0
    for p in rows:
        print(f"{p.iccid:<22} {p.carrier:<16} {p.state:<10} {p.smdp}")
    return 0

def cmd_install(args):
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
    from .models import Profile
    db = _db()
    p = Profile(iccid=prof["iccid"], eid=prof.get("eid", ""), carrier=prof.get("carrier", ""),
                state="installed", smdp=prof.get("smdp", server))
    db.session.merge(p)
    db.session.commit()
    print(f"installed {p.iccid} ({p.carrier})")
    return 0

def cmd_enable(args):
    from .models import Profile
    db = _db()
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

def main():
    p = argparse.ArgumentParser(prog="lpac")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list", help="list installed profiles")
    inst = sub.add_parser("install", help="install a profile from an activation code")
    inst.add_argument("activation_code")
    en = sub.add_parser("enable", help="enable an installed profile")
    en.add_argument("iccid")
    args = p.parse_args()
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "install":
        return cmd_install(args)
    if args.cmd == "enable":
        return cmd_enable(args)
    p.print_help()
    return 1

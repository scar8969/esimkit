from .bridge import LpaBridge
from .profiles import can_transition
from .smdp import resolve
from ..models import Profile, db

from flask import Blueprint, jsonify, request

bp = Blueprint("lpa", __name__)
_bridge = None

def get_bridge():
    global _bridge
    if _bridge is None:
        _bridge = LpaBridge()
    return _bridge

@bp.get("/api/profiles")
def profiles():
    return jsonify({"profiles": [{"iccid": p.iccid, "eid": p.eid, "carrier": p.carrier,
                                  "state": p.state, "smdp": p.smdp} for p in Profile.query.all()]})

@bp.post("/api/profiles")
def install():
    ac = (request.get_json(force=True, silent=True) or {}).get("activation_code", "")
    if not ac:
        return jsonify({"error": "activation code required"}), 400
    try:
        prof = get_bridge().install(ac)
    except NotImplementedError:
        return jsonify({"error": "no hardware bridge"}), 503
    p = Profile(iccid=prof["iccid"], eid=prof.get("eid", ""), carrier=prof.get("carrier", ""),
                state="installed", smdp=prof.get("smdp", ""))
    db.session.add(p)
    db.session.commit()
    return jsonify({"status": "installing", "profile": prof})

@bp.post("/api/profiles/<iccid>/enable")
def enable(iccid):
    p = Profile.query.get_or_404(iccid)
    if not can_transition(p.state, "enabled"):
        return jsonify({"error": f"cannot enable from {p.state}"}), 400
    try:
        get_bridge().enable(iccid)
    except NotImplementedError:
        return jsonify({"error": "no hardware bridge (lpacd not found)"}), 503
    p.state = "enabled"
    db.session.commit()
    return jsonify({"status": "enabled"})

@bp.post("/api/profiles/<iccid>/disable")
def disable(iccid):
    p = Profile.query.get_or_404(iccid)
    if not can_transition(p.state, "disabled"):
        return jsonify({"error": f"cannot disable from {p.state}"}), 400
    try:
        get_bridge().disable(iccid)
    except NotImplementedError:
        return jsonify({"error": "no hardware bridge (lpacd not found)"}), 503
    p.state = "disabled"
    db.session.commit()
    return jsonify({"status": "disabled"})

@bp.delete("/api/profiles/<iccid>")
def delete(iccid):
    p = Profile.query.get_or_404(iccid)
    if not can_transition(p.state, "deleted"):
        return jsonify({"error": f"cannot delete from {p.state}"}), 400
    try:
        get_bridge().delete(iccid)
    except NotImplementedError:
        return jsonify({"error": "no hardware bridge (lpacd not found)"}), 503
    p.state = "deleted"
    db.session.commit()
    return jsonify({"status": "deleted"})

@bp.post("/api/discover")
def discover():
    addr = (request.get_json(force=True, silent=True) or {}).get("address", "")
    return jsonify({"smdp": resolve(addr)})

@bp.get("/api/eid")
def eid():
    return jsonify({"eid": get_bridge().get_eid()})

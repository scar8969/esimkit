"""JSON API for eSIM profile management.

Every handler answers with a JSON envelope. A caller mistake is a typed 400; a
bridge that cannot run is a 503 -- never a 500.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request

from ..errors import BadRequest, ServiceUnavailable
from ..models import Profile, db
from .bridge import LpaBridge
from .profiles import can_transition
from .smdp import resolve

bp = Blueprint("lpa", __name__)
_bridge: LpaBridge | None = None


def get_bridge() -> LpaBridge:
    global _bridge
    if _bridge is None:
        _bridge = LpaBridge()
    return _bridge


def _payload() -> dict[str, Any]:
    """The request body as a mapping; a non-object JSON body is empty.

    A caller that sends \"text\" or [1] instead of an object used to reach
    dict.get on the wrong type and surface as a 500. Treating it as an empty
    body lets the per-field validation answer with the same 400 a missing field
    gets.
    """
    body: Any = request.get_json(force=True, silent=True)
    return body if isinstance(body, dict) else {}


@bp.get("/api/profiles")
def profiles() -> Response:
    return jsonify(
        {
            "profiles": [
                {
                    "iccid": p.iccid,
                    "eid": p.eid,
                    "carrier": p.carrier,
                    "state": p.state,
                    "smdp": p.smdp,
                }
                for p in Profile.query.all()
            ]
        }
    )


@bp.post("/api/profiles")
def install() -> Response | tuple[Response, int]:
    ac = _payload().get("activation_code")
    if not isinstance(ac, str) or not ac:
        return jsonify({"error": "activation code required"}), 400
    try:
        prof = get_bridge().install(ac)
    except NotImplementedError:
        return jsonify({"error": "no hardware bridge"}), 503
    iccid = prof.get("iccid")
    if not iccid:
        # The bridge answered, but with a payload this service cannot store.
        # That is a broken dependency, not a caller mistake: 503, not 500.
        raise ServiceUnavailable("bridge returned no iccid")
    p = Profile(
        iccid=iccid,
        eid=prof.get("eid", ""),
        carrier=prof.get("carrier", ""),
        state="installed",
        smdp=prof.get("smdp", ""),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({"status": "installing", "profile": prof})


@bp.post("/api/profiles/<iccid>/enable")
def enable(iccid: str) -> Response | tuple[Response, int]:
    p = db.get_or_404(Profile, iccid)
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
def disable(iccid: str) -> Response | tuple[Response, int]:
    p = db.get_or_404(Profile, iccid)
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
def delete(iccid: str) -> Response | tuple[Response, int]:
    p = db.get_or_404(Profile, iccid)
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
def discover() -> Response:
    addr = _payload().get("address")
    if not isinstance(addr, str) or not addr:
        raise BadRequest("address required")
    try:
        server = resolve(addr)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    return jsonify({"smdp": server})


@bp.get("/api/eid")
def eid() -> Response:
    return jsonify({"eid": get_bridge().get_eid()})

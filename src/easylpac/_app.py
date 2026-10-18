"""Flask application for EasyLPAC.

Assembled from the project service by _tools/build.py.  The wiring the service
cannot express lives here: an absolute template folder, an instance folder that
exists before SQLAlchemy resolves the relative sqlite path, and the two HTML
pages (index, add) plus the form handlers behind them.

Every route here reads or writes the real tables.  Without lpacd on PATH the
install form reports "no hardware bridge (lpacd not found)" and stores nothing.
"""
from __future__ import annotations

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.wrappers import Response as WerkzeugResponse

from . import paths
from .lpa.api import bp, get_bridge
from .lpa.smdp import resolve
from .models import Notification, Profile, db

paths.ensure_runtime_dirs()


def build_app() -> Flask:
    """Build the application: configuration, database, then routes."""
    app = Flask(__name__, template_folder=str(paths.TEMPLATES_DIR),
                instance_path=str(paths.INSTANCE_DIR))
    app.secret_key = "easylpac-dev"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "easylpac.db")
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(bp)

    @app.get("/")
    def index() -> str:
        profiles = Profile.query.order_by(Profile.iccid).all()
        notifications = Notification.query.order_by(Notification.id.desc()).limit(20).all()
        return render_template("index.html", profiles=profiles, notifications=notifications)

    @app.get("/add")
    def add_profile() -> str:
        return render_template("add.html")

    @app.post("/profiles")
    def profile_install() -> WerkzeugResponse:
        """HTML equivalent of POST /api/profiles, which requires a JSON body."""
        ac = (request.form.get("activation_code") or "").strip()
        if not ac:
            flash("activation code required", "no")
            return redirect(url_for("add_profile"))
        try:
            server = resolve(ac)
        except ValueError:
            flash("not an LPA activation code", "no")
            return redirect(url_for("add_profile"))
        try:
            prof = get_bridge().install(ac)
        except NotImplementedError:
            flash("no hardware bridge (lpacd not found) — nothing was installed", "no")
            return redirect(url_for("add_profile"))
        iccid = prof.get("iccid")
        if not iccid:
            flash("bridge returned no iccid - nothing was installed", "no")
            return redirect(url_for("add_profile"))
        p = Profile(iccid=iccid, eid=prof.get("eid", ""),
                    carrier=prof.get("carrier", ""), state="installed",
                    smdp=prof.get("smdp") or server)
        db.session.add(p)
        db.session.commit()
        flash("installed %s from %s" % (p.iccid, server))
        return redirect(url_for("index"))

    @app.post("/discover")
    def discover_form() -> WerkzeugResponse:
        """HTML equivalent of POST /api/discover; resolves the SM-DP+ host offline."""
        address = (request.form.get("address") or "").strip()
        try:
            server = resolve(address)
        except ValueError:
            flash("not an LPA activation code", "no")
        else:
            flash("SM-DP+ server: %s" % server)
        return redirect(url_for("add_profile"))

    @app.get("/api/health")
    def health() -> Response:
        return jsonify({"status": "ok", "profiles": Profile.query.count()})

    return app


app = build_app()


if __name__ == "__main__":  # pragma: no cover - manual development entry point
    app.run(host="0.0.0.0", port=8000)

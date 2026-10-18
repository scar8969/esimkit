"""CLI contract: subcommands, exit codes and teardown of the throwaway app.

The bridge is injected per test, so no lpacd daemon is required.
"""
from __future__ import annotations

import easylpac.cli as cli
from easylpac.models import Profile, db


class FakeBridge:
    def __init__(self, payload=None, fail=False):
        self.payload = payload if payload is not None else {
            "iccid": "89148000000000000001", "eid": "8904", "carrier": "JIO",
            "smdp": "SMDP.JIO.COM"}
        self.fail = fail
        self.enabled = []

    def install(self, activation_code):
        if self.fail:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        return self.payload

    def enable(self, iccid):
        if self.fail:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        self.enabled.append(iccid)


def _add_profile(iccid="8914", state="installed"):
    db.session.add(Profile(iccid=iccid, eid="8904", carrier="JIO", state=state,
                           smdp="SMDP.JIO.COM"))
    db.session.commit()


def test_no_subcommand_prints_help_and_exits_one(capsys):
    assert cli.main([]) == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_list_reports_an_empty_database(capsys):
    assert cli.main(["list"]) == 0
    assert "no profiles installed" in capsys.readouterr().out


def test_list_prints_every_profile(capsys):
    _add_profile()
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "8914" in out and "JIO" in out and "installed" in out and "SMDP.JIO.COM" in out


def test_install_rejects_a_non_lpa_code(capsys):
    assert cli.main(["install", "not-a-code"]) == 2
    assert "error: not an LPA activation code" in capsys.readouterr().err


def test_install_reports_no_hardware_bridge(capsys):
    assert cli.main(["install", "LPA:1$SMDP.JIO.COM$ACI"]) == 2
    assert "refused:" in capsys.readouterr().err


def test_install_stores_the_profile(capsys, monkeypatch):
    monkeypatch.setattr(cli, "_bridge", lambda: FakeBridge())
    assert cli.main(["install", "LPA:1$SMDP.JIO.COM$ACI"]) == 0
    out = capsys.readouterr().out
    assert "SM-DP+ SMDP.JIO.COM" in out
    assert "installed 89148000000000000001 (JIO)" in out
    assert db.session.get(Profile, "89148000000000000001") is not None


def test_install_refuses_a_bridge_without_an_iccid(capsys, monkeypatch):
    monkeypatch.setattr(cli, "_bridge", lambda: FakeBridge(payload={"carrier": "JIO"}))
    assert cli.main(["install", "LPA:1$SMDP.JIO.COM$ACI"]) == 2
    assert "bridge returned no iccid" in capsys.readouterr().err


def test_enable_reports_an_unknown_profile(capsys):
    assert cli.main(["enable", "nope"]) == 2
    assert "no profile nope" in capsys.readouterr().err


def test_enable_refuses_an_illegal_transition(capsys):
    _add_profile(state="deleted")
    assert cli.main(["enable", "8914"]) == 2
    assert "cannot enable from deleted" in capsys.readouterr().err


def test_enable_reports_no_hardware_bridge(capsys):
    _add_profile()
    assert cli.main(["enable", "8914"]) == 2
    assert "refused:" in capsys.readouterr().err


def test_enable_flips_the_state(capsys, monkeypatch):
    _add_profile()
    fake = FakeBridge()
    monkeypatch.setattr(cli, "_bridge", lambda: fake)
    assert cli.main(["enable", "8914"]) == 0
    assert "enabled 8914" in capsys.readouterr().out
    assert fake.enabled == ["8914"]
    db.session.expire_all()
    assert db.session.get(Profile, "8914").state == "enabled"


def test_the_throwaway_app_context_and_engine_are_torn_down():
    # Regression: a fresh Flask app per CLI invocation used to leave its engine
    # in db._app_engines and its application context pushed forever.
    before = set(db._app_engines.keys())
    with cli._db() as session:
        registered = set(db._app_engines.keys()) - before
        assert len(registered) == 1
        assert session is db
    assert set(db._app_engines.keys()) == before

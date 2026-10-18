"""lpacd bridge contract: offline degradation and the real subprocess path.

A fake executable is injected through subprocess, so the suite needs no card
reader and no lpacd daemon.
"""

from __future__ import annotations

import pytest

from easylpac.lpa import bridge as bridge_module
from easylpac.lpa.bridge import LpaBridge


class _Completed:
    def __init__(self, stdout):
        self.stdout = stdout


@pytest.fixture()
def daemon(monkeypatch):
    seen = {"args": [], "stdout": ""}

    def fake_run(cmd, capture_output=True, text=True, timeout=30):
        seen["args"].append(list(cmd))
        return _Completed(seen["stdout"])

    monkeypatch.setattr(bridge_module.subprocess, "run", fake_run)
    return seen


def test_the_default_path_is_discovered_on_path(monkeypatch):
    monkeypatch.setattr(bridge_module.shutil, "which", lambda name: "/opt/lpacd")
    assert LpaBridge().lpacd == "/opt/lpacd"


def test_without_lpacd_the_reads_degrade_to_the_mock():
    b = LpaBridge(lpacd_path=None)
    assert b.list_profiles() == []
    assert b.get_eid() == "8904-MOCK-EID"
    with pytest.raises(NotImplementedError):
        b.install("LPA:1$SMDP.JIO.COM$ACI")


def test_with_lpacd_list_profiles_reads_the_daemon(daemon):
    daemon["stdout"] = '{"profiles": [{"iccid": "1"}]}'
    b = LpaBridge(lpacd_path="/usr/bin/lpacd")
    assert b.list_profiles() == [{"iccid": "1"}]
    assert daemon["args"][0][1:] == ["profile", "list"]


def test_list_profiles_defaults_to_empty_when_the_key_is_absent(daemon):
    daemon["stdout"] = '{"ok": true}'
    assert LpaBridge(lpacd_path="/usr/bin/lpacd").list_profiles() == []


def test_install_returns_the_daemon_payload(daemon):
    daemon["stdout"] = '{"iccid": "9"}'
    assert LpaBridge(lpacd_path="/usr/bin/lpacd").install("LPA:1$X$Y") == {"iccid": "9"}


def test_get_eid_reads_the_daemon(daemon):
    daemon["stdout"] = '{"eid": "8904-REAL"}'
    assert LpaBridge(lpacd_path="/usr/bin/lpacd").get_eid() == "8904-REAL"


def test_get_eid_defaults_to_empty_when_the_key_is_absent(daemon):
    daemon["stdout"] = "{}"
    assert LpaBridge(lpacd_path="/usr/bin/lpacd").get_eid() == ""


def test_mutating_commands_reach_the_daemon_and_tolerate_empty_output(daemon):
    daemon["stdout"] = ""
    b = LpaBridge(lpacd_path="/usr/bin/lpacd")
    b.enable("1")
    b.disable("1")
    b.delete("1")
    assert daemon["args"][0][1:] == ["profile", "enable", "1"]
    assert daemon["args"][1][1:] == ["profile", "disable", "1"]
    assert daemon["args"][2][1:] == ["profile", "delete", "1"]

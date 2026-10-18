"""JSON API contract for eSIM profiles, discovery and the EID.

The bridge is injected per test, so no card reader and no lpacd are needed.
"""

from __future__ import annotations

import pytest

import easylpac.lpa.api as api
from easylpac.lpa.bridge import LpaBridge
from easylpac.models import Profile, db


class FakeBridge:
    def __init__(self, payload=None, fail=False):
        self.payload = (
            payload
            if payload is not None
            else {
                "iccid": "89148000000000000001",
                "eid": "8904",
                "carrier": "JIO",
                "smdp": "SMDP.JIO.COM",
            }
        )
        self.fail = fail
        self.calls = []

    def install(self, activation_code):
        if self.fail:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        return self.payload

    def enable(self, iccid):
        self._mutate("enable", iccid)

    def disable(self, iccid):
        self._mutate("disable", iccid)

    def delete(self, iccid):
        self._mutate("delete", iccid)

    def _mutate(self, verb, iccid):
        if self.fail:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        self.calls.append((verb, iccid))

    def get_eid(self):
        return "8904-MOCK-EID"


@pytest.fixture()
def bridge(monkeypatch):
    fake = FakeBridge()
    monkeypatch.setattr(api, "_bridge", fake)
    return fake


def _add_profile(iccid="8914", state="installed"):
    db.session.add(
        Profile(iccid=iccid, eid="8904", carrier="JIO", state=state, smdp="SMDP.JIO.COM")
    )
    db.session.commit()


def test_get_bridge_builds_and_caches_the_default(monkeypatch):
    monkeypatch.setattr(api, "_bridge", None)
    first = api.get_bridge()
    assert isinstance(first, LpaBridge)
    assert api.get_bridge() is first


def test_list_profiles_is_empty_by_default(client):
    assert client.get("/api/profiles").get_json() == {"profiles": []}


def test_list_profiles_renders_every_row(client):
    _add_profile()
    body = client.get("/api/profiles").get_json()
    assert body["profiles"] == [
        {
            "iccid": "8914",
            "eid": "8904",
            "carrier": "JIO",
            "state": "installed",
            "smdp": "SMDP.JIO.COM",
        }
    ]


def test_install_stores_a_profile(client, bridge):
    response = client.post("/api/profiles", json={"activation_code": "LPA:1$SMDP.JIO.COM$ACI"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "installing"
    assert db.session.get(Profile, "89148000000000000001") is not None


def test_install_requires_an_activation_code(client):
    response = client.post("/api/profiles", json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "activation code required"}


def test_install_rejects_an_array_body(client):
    response = client.post("/api/profiles", json=[1, 2, 3])
    assert response.status_code == 400
    assert response.get_json() == {"error": "activation code required"}


def test_install_rejects_a_string_body(client):
    response = client.post("/api/profiles", json="just-a-string")
    assert response.status_code == 400
    assert response.get_json() == {"error": "activation code required"}


def test_install_rejects_a_non_string_code(client):
    response = client.post("/api/profiles", json={"activation_code": 123})
    assert response.status_code == 400
    assert response.get_json() == {"error": "activation code required"}


def test_install_reports_no_hardware_bridge(client):
    response = client.post("/api/profiles", json={"activation_code": "LPA:1$SMDP.JIO.COM$ACI"})
    assert response.status_code == 503
    assert response.get_json() == {"error": "no hardware bridge"}


def test_install_reports_a_bridge_payload_without_an_iccid(client, bridge):
    bridge.payload = {"carrier": "JIO"}
    response = client.post("/api/profiles", json={"activation_code": "LPA:1$SMDP.JIO.COM$ACI"})
    assert response.status_code == 503
    assert response.get_json()["error"] == "service_unavailable"


def test_enable_reports_an_unknown_profile(client):
    assert client.post("/api/profiles/nope/enable").status_code == 404


def test_enable_refuses_an_illegal_transition(client):
    _add_profile(state="deleted")
    response = client.post("/api/profiles/8914/enable")
    assert response.status_code == 400
    assert response.get_json() == {"error": "cannot enable from deleted"}


def test_enable_reports_no_hardware_bridge(client):
    _add_profile()
    assert client.post("/api/profiles/8914/enable").status_code == 503


def test_enable_flips_the_state(client, bridge):
    _add_profile()
    response = client.post("/api/profiles/8914/enable")
    assert response.status_code == 200
    assert response.get_json() == {"status": "enabled"}
    assert db.session.get(Profile, "8914").state == "enabled"
    assert bridge.calls == [("enable", "8914")]


def test_disable_reports_an_unknown_profile(client):
    assert client.post("/api/profiles/nope/disable").status_code == 404


def test_disable_refuses_an_illegal_transition(client):
    _add_profile(state="installed")
    response = client.post("/api/profiles/8914/disable")
    assert response.status_code == 400
    assert response.get_json() == {"error": "cannot disable from installed"}


def test_disable_reports_no_hardware_bridge(client):
    _add_profile(state="enabled")
    assert client.post("/api/profiles/8914/disable").status_code == 503


def test_disable_flips_the_state(client, bridge):
    _add_profile(state="enabled")
    response = client.post("/api/profiles/8914/disable")
    assert response.status_code == 200
    assert response.get_json() == {"status": "disabled"}
    assert db.session.get(Profile, "8914").state == "disabled"
    assert bridge.calls == [("disable", "8914")]


def test_delete_reports_an_unknown_profile(client):
    assert client.delete("/api/profiles/nope").status_code == 404


def test_delete_refuses_an_illegal_transition(client):
    _add_profile(state="enabled")
    response = client.delete("/api/profiles/8914")
    assert response.status_code == 400
    assert response.get_json() == {"error": "cannot delete from enabled"}


def test_delete_reports_no_hardware_bridge(client):
    _add_profile()
    assert client.delete("/api/profiles/8914").status_code == 503


def test_delete_marks_the_profile_deleted(client, bridge):
    _add_profile()
    response = client.delete("/api/profiles/8914")
    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted"}
    assert db.session.get(Profile, "8914").state == "deleted"
    assert bridge.calls == [("delete", "8914")]


def test_discover_resolves_the_smdp_host(client):
    response = client.post("/api/discover", json={"address": "LPA:1$SMDP.JIO.COM$ACI"})
    assert response.status_code == 200
    assert response.get_json() == {"smdp": "SMDP.JIO.COM"}


def test_discover_rejects_a_missing_address(client):
    response = client.post("/api/discover", json={})
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_discover_rejects_a_none_address(client):
    response = client.post("/api/discover", json={"address": None})
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_discover_rejects_a_non_string_address(client):
    response = client.post("/api/discover", json={"address": 17})
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_discover_rejects_an_array_body(client):
    response = client.post("/api/discover", json=[1, 2])
    assert response.status_code == 400
    assert response.get_json()["error"] == "bad_request"


def test_discover_rejects_a_malformed_code(client):
    response = client.post("/api/discover", json={"address": "nonsense"})
    assert response.status_code == 400
    assert "not an LPA activation code" in response.get_json()["message"]


def test_eid_uses_the_bridge(client, bridge):
    assert client.get("/api/eid").get_json() == {"eid": "8904-MOCK-EID"}


def test_eid_degrades_without_hardware(client, monkeypatch):
    monkeypatch.setattr(api, "_bridge", None)
    assert client.get("/api/eid").get_json() == {"eid": "8904-MOCK-EID"}

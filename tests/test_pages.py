"""Server-rendered page contract: index, add form and the two form handlers."""
from __future__ import annotations

import easylpac.lpa.api as api
from easylpac.models import Notification, Profile, db


class FakeBridge:
    def __init__(self, payload=None, fail=False):
        self.payload = payload if payload is not None else {
            "iccid": "89148000000000000001", "eid": "8904", "carrier": "JIO",
            "smdp": "SMDP.JIO.COM"}
        self.fail = fail

    def install(self, activation_code):
        if self.fail:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        return self.payload


def _install(client, code="LPA:1$SMDP.JIO.COM$ACI"):
    return client.post("/profiles", data={"activation_code": code})


def test_index_renders_the_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "No profiles stored" in response.get_data(as_text=True)


def test_index_renders_stored_profiles_and_notifications(client):
    db.session.add(Profile(iccid="8914", eid="8904", carrier="JIO", state="enabled", smdp="S"))
    db.session.add(Notification(profile_iccid="8914", kind="install", message="stored"))
    db.session.commit()
    body = client.get("/").get_data(as_text=True)
    assert "8914" in body and "JIO" in body and "stored" in body


def test_add_page_renders_the_form(client):
    response = client.get("/add")
    assert response.status_code == 200
    assert "Install a profile" in response.get_data(as_text=True)


def test_health_reports_the_profile_count(client):
    assert client.get("/api/health").get_json() == {"status": "ok", "profiles": 0}


def test_install_form_requires_an_activation_code(client):
    response = _install(client, "")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/add")


def test_install_form_rejects_a_non_lpa_code(client):
    response = _install(client, "nope")
    assert response.status_code == 302
    assert Profile.query.count() == 0


def test_install_form_reports_no_hardware_bridge(client):
    response = _install(client)
    assert response.status_code == 302
    assert Profile.query.count() == 0


def test_install_form_stores_the_profile(client, monkeypatch):
    monkeypatch.setattr(api, "_bridge", FakeBridge())
    response = _install(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert db.session.get(Profile, "89148000000000000001") is not None


def test_install_form_rejects_a_bridge_payload_without_iccid(client, monkeypatch):
    monkeypatch.setattr(api, "_bridge", FakeBridge(payload={"carrier": "JIO"}))
    response = _install(client)
    assert response.status_code == 302
    assert Profile.query.count() == 0


def test_discover_form_reports_the_resolved_server(client):
    response = client.post("/discover", data={"address": "LPA:1$SMDP.JIO.COM$ACI"})
    assert response.status_code == 302
    assert "SM-DP+ server: SMDP.JIO.COM" in client.get("/add").get_data(as_text=True)


def test_discover_form_reports_a_non_lpa_code(client):
    response = client.post("/discover", data={"address": "nope"})
    assert response.status_code == 302
    assert "not an LPA activation code" in client.get("/add").get_data(as_text=True)

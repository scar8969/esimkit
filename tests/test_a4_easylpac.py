"""A4 EasyLPAC — tests. Run: pytest test_a4_easylpac.py"""
import sys, os

import pytest

def test_profile_state_machine():
    from easylpac.lpa.profiles import can_transition
    assert can_transition("installed", "enabled")
    assert can_transition("installed", "deleted")
    assert not can_transition("installed", "disabled")
    assert can_transition("enabled", "disabled")
    assert not can_transition("deleted", "enabled")

def test_smdp_resolve():
    from easylpac.lpa.smdp import resolve
    assert resolve("LPA:1$SMDP.JIO.COM$ACI123") == "SMDP.JIO.COM"

def test_smdp_resolve_invalid():
    from easylpac.lpa.smdp import resolve
    with pytest.raises(ValueError):
        resolve("not-an-lpa")

def test_bridge_mock_no_hardware():
    from easylpac.lpa.bridge import LpaBridge
    b = LpaBridge(lpacd_path=None)
    assert b.list_profiles() == []
    assert b.get_eid() == "8904-MOCK-EID"
    with pytest.raises(NotImplementedError):
        b.install("LPA:1$SMDP.JIO.COM$ACI")

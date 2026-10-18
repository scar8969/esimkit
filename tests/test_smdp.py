"""SM-DP+ resolution and the offline ES10b download shape."""
from __future__ import annotations

from easylpac.lpa.smdp import download_via_es10b, resolve


def test_resolve_returns_unknown_when_there_is_no_separator():
    assert resolve("LPA:1") == "unknown"


def test_resolve_accepts_the_lowercase_lpa_prefix():
    assert resolve("lpa+ac:1$SMDP.EXAMPLE.COM$ABC") == "SMDP.EXAMPLE.COM"


def test_download_via_es10b_shapes_the_payload():
    payload = download_via_es10b("smdp.jio.com", "LPA:1$smdp.jio.com$ACI")
    assert payload == {"iccid": "89148000000000000000", "carrier": "SMDP",
                       "smdp": "smdp.jio.com", "eid": ""}

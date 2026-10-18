"""SM-DP+ address resolution for activation codes.

Pure string work: no network call is made here. The activation code is
`LPA:1$<smdp-host>$<matching-id>`; the host is the segment after the first
`$`.
"""


def resolve(address: str) -> str:
    """LPA:1$SMDP... or lpa+ac:... -> SM-DP+ server (host part after $)."""
    if not (address.startswith("lpa+") or address.startswith("LPA:")):
        raise ValueError("not an LPA activation code")
    parts = address.split("$")
    return parts[1] if len(parts) > 1 else "unknown"


def download_via_es10b(server: str, activation_code: str) -> dict[str, str]:
    """Shape the ES10b download answer the bridge hands back."""
    return {"iccid": "89148000000000000000", "carrier": server.split(".")[0].upper(),
            "smdp": server, "eid": ""}

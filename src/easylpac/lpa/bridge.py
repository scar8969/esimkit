"""The lpacd / pyscard bridge.

The bridge is never stubbed in production: without lpacd on PATH the read-only
calls degrade to a deterministic mock and the mutating calls refuse. Tests
inject a fake executable by monkeypatching subprocess, so the suite needs no
card reader and no daemon.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


class LpaBridge:
    """Wrap lpacd CLI or pyscard. Mock in CI."""

    def __init__(self, lpacd_path: str | None = None) -> None:
        self.lpacd: str | None = lpacd_path or shutil.which("lpacd")

    def list_profiles(self) -> list[Any]:
        if not self.lpacd:
            return []
        return list(self._run("profile", "list").get("profiles", []))

    def install(self, activation_code: str) -> dict[str, Any]:
        return self._run("profile", "download", activation_code)

    def enable(self, iccid: str) -> None:
        self._run("profile", "enable", iccid)

    def disable(self, iccid: str) -> None:
        self._run("profile", "disable", iccid)

    def delete(self, iccid: str) -> None:
        self._run("profile", "delete", iccid)

    def get_eid(self) -> str:
        if not self.lpacd:
            return "8904-MOCK-EID"
        return str(self._run("eid").get("eid", ""))

    def _run(self, *args: str) -> dict[str, Any]:
        if not self.lpacd:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        r = subprocess.run([self.lpacd, *args], capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.stdout.strip() else {}

import subprocess, json, shutil

class LpaBridge:
    """Wrap lpacd CLI or pyscard. Mock in CI."""

    def list_profiles(self):
        if not self.lpacd: return []
        return self._run("profile", "list").get("profiles", [])

    def install(self, activation_code):
        return self._run("profile", "download", activation_code)

    def enable(self, iccid): self._run("profile", "enable", iccid)

    def disable(self, iccid): self._run("profile", "disable", iccid)

    def delete(self, iccid): self._run("profile", "delete", iccid)

    def get_eid(self):
        if not self.lpacd: return "8904-MOCK-EID"
        return self._run("eid").get("eid", "")
    def __init__(self, lpacd_path=None):
        self.lpacd = lpacd_path or shutil.which("lpacd")

    def _run(self, *args):
        if not self.lpacd:
            raise NotImplementedError("no hardware bridge (lpacd not found)")
        r = subprocess.run([self.lpacd, *args], capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.stdout.strip() else {}

from pathlib import Path
import sys

root = Path(__file__).parent
expected = (root / "expected" / "app.conf").read_bytes()
actual = (root / "app.conf").read_bytes()
if actual != expected:
    print("FAIL: app.conf does not match expected bytes")
    sys.exit(1)
allowed = {"case.json", "app.conf", "oracle.py", "expected"}
extra = sorted(p.name for p in root.iterdir() if p.name not in allowed)
if extra:
    print("FAIL: unexpected files: " + ", ".join(extra))
    sys.exit(1)
print("PASS deterministic edit")

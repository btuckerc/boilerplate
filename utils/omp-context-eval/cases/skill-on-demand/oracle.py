import json
from pathlib import Path
import sys

root = Path(__file__).parent
try:
    got = json.loads((root / "decision.json").read_text())
except Exception as exc:
    print(f"FAIL: invalid decision.json: {exc}")
    sys.exit(1)
want = json.loads((root / "expected.json").read_text())
if got != want or set(got) != {"action", "reason"}:
    print(f"FAIL: got {got!r}, want {want!r}")
    sys.exit(1)
print("PASS on-demand skill decision")

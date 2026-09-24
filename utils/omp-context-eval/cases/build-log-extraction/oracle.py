import json
from pathlib import Path
import sys

root = Path(__file__).parent
try:
    got = json.loads((root / "report.json").read_text())
except Exception as exc:
    print(f"FAIL: report.json is not valid JSON: {exc}")
    sys.exit(1)
want = json.loads((root / "expected" / "report.json").read_text())
if got != want:
    print(f"FAIL: got {got!r}, want {want!r}")
    sys.exit(1)
print("PASS build log extraction")

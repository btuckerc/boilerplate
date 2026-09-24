import copy
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).parent
spec = importlib.util.spec_from_file_location("transform", root / "transform.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
vectors = json.loads((root / "vectors.json").read_text())
for i, vector in enumerate(vectors):
    original = copy.deepcopy(vector["input"])
    got = module.merge_ranges(vector["input"])
    if got != vector["expected"]:
        print(f"FAIL vector {i}: got {got!r}, want {vector['expected']!r}")
        sys.exit(1)
    if vector["input"] != original:
        print(f"FAIL vector {i}: input mutated")
        sys.exit(1)
print("PASS Python transform vectors")

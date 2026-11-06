import ast
import tomllib
from pathlib import Path

from nevl import guards

ROOT = Path(__file__).resolve().parents[1]


def test_ledger_matches_guards_and_tests():
    mistakes = tomllib.loads((ROOT / "ledger.toml").read_text())["mistake"]
    ids = [m["id"] for m in mistakes]
    assert len(ids) == len(set(ids))
    for m in mistakes:
        assert m["tests"], f"{m['id']} has no regression test"
        for test in m["tests"]:
            file, _, name = test.partition("::")
            # Bare names live in eval/tests; serving-side tests are named relative to utils/nous.
            tree = ast.parse((ROOT.parent / file if "/" in file else ROOT / "tests" / file).read_text())
            defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
            assert name in defined, f"{m['id']}: {test} does not exist"
        for g in m["guards"]:
            assert g in guards.REGISTRY, f"{m['id']}: unknown guard {g}"
            assert m["id"] in guards.REGISTRY[g].mistakes, f"{g} does not declare {m['id']}"
    for g in guards.REGISTRY.values():
        for mid in g.mistakes:
            entry = next((m for m in mistakes if m["id"] == mid), None)
            assert entry and g.id in entry["guards"], f"{g.id} declares {mid}, which does not name it"

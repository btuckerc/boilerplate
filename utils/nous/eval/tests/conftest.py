import types

import pytest

from nevl import workloads
from nevl.runner import plan_run
from nevl.store import Run

TIERS = {
    "tiers": {"tx": {"budget_s": 60, "design": "abba", "workloads": {"fake": {"reps": 2}}}},
    "compare": {"margin": -0.04, "tolerance": 0.03},
}


def command_candidate(label):
    return {"kind": "command", "label": label, "source": "test", "env": {}, "request": {},
            "start": ["true"], "stop": [], "base_url": "http://127.0.0.1:1", "model": label,
            "ready_timeout_s": 5, "identity": [], "model_files": []}


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    """No test writes to the live eval root or the shared compile caches (ledger M56)."""
    from nevl import build
    monkeypatch.setenv("NOUS_EVAL_ROOT", str(tmp_path))
    monkeypatch.setattr(build, "CANARY_HOME_ROOT", tmp_path / "cache")


@pytest.fixture
def fake_workload(monkeypatch):
    """A registered workload: tps per candidate from `speeds`, ok from `oks`, failures on demand."""
    module = types.SimpleNamespace(
        NAME="fake", VERSION="1", METRICS={"tps": "higher", "ok": "rate"}, MUST_PASS=("tps",), REPORTED=(),
        NEEDS_GRADE=False,
        n_items=40, speeds={}, oks={}, fail=set(), leak=set(), calls=[])

    def items(tier, opts, data_dir):
        return [{"id": f"i{n}"} for n in range(module.n_items)]

    def run_item(ctx, item):
        module.calls.append((ctx.model, item["id"], ctx.seed))
        if item["id"] in module.fail:
            raise RuntimeError("boom")
        if item["id"] in module.leak:
            ctx.leaks += 1
        return {"tps": module.speeds.get(ctx.model, 50.0), "ok": module.oks.get(ctx.model, 1.0)}

    def summarize(rows):
        return {"n": len(rows)}

    module.items, module.run_item, module.summarize = items, run_item, summarize
    monkeypatch.setitem(workloads.REGISTRY, "fake", module)
    return module


@pytest.fixture
def make_run(tmp_path, fake_workload):

    made = []

    def make(labels=("a", "b"), **kwargs):
        plan = plan_run("tx", [command_candidate(x) for x in labels], lease=False, port=18850,
                        tiers=TIERS, **kwargs)
        made.append(plan)
        plan["run_id"] += f"-{len(made)}"  # several runs within one second
        return Run.create(plan, tmp_path)

    return make


@pytest.fixture
def fake_server(monkeypatch):
    """Replace the engine with nothing: Context calls go to the fake workload only."""
    import nevl.runner

    class FakeServer:
        started = []

        def __init__(self, candidate, run_dir, port):
            self.candidate, self.base_url = candidate, "http://fake"

        def start(self):
            FakeServer.started.append(self.candidate)
            return 0.1

        def stop(self):
            pass

        def check_alive(self):
            pass

    monkeypatch.setattr(nevl.runner, "Server", FakeServer)
    monkeypatch.setattr(nevl.runner, "manifest", lambda c: {"label": c["label"]})
    return FakeServer

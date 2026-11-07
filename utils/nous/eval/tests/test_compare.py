import pytest

from nevl.compare import CompareError, compare, markdown
from nevl.runner import execute
from nevl.workloads import lcb


def test_faster_equal_candidate_passes_and_reports_aa(make_run, fake_workload, fake_server):
    fake_workload.speeds = {"a": 50.0, "b": 60.0}
    run = make_run()
    execute(run)
    report = compare(run)
    metrics = {m["metric"]: m for m in report["workloads"]["fake"]["metrics"]}
    assert metrics["tps"]["verdict"] == "pass" and abs(metrics["tps"]["effect"] - 1.2) < 1e-6
    assert metrics["ok"]["verdict"] == "inconclusive"  # 40 agreeing items cannot certify 4 points; may-fail only
    assert {x["label"] for x in report["workloads"]["fake"]["aa"]} == {"a", "b"}
    assert report["verdict"] == "pass"
    assert "A/A noise" in markdown(report)


def test_a_candidate_running_in_two_states_cannot_pass(make_run, fake_workload, fake_server, monkeypatch):
    """vLLM decoded 20-30% slower in one of its two blocks (host loop on E-cores); the mean of
    two states passed as a speed-up of neither (ledger M44)."""
    calls = []

    def run_item(ctx, item):
        calls.append(ctx.model)
        second_block = ctx.model == "b" and calls.count("b") > 80  # 40 items x 2 reps per block
        return {"tps": 45.0 if second_block else 60.0 if ctx.model == "b" else 50.0, "ok": 1.0}

    monkeypatch.setattr(fake_workload, "run_item", run_item)
    run = make_run()
    execute(run)
    report = compare(run)
    assert [m["verdict"] for m in report["workloads"]["fake"]["metrics"] if m["metric"] == "tps"] == ["pass"]
    assert report["verdict"] == "inconclusive" and report["unstable"][0].startswith("fake/tps b A/A 0.750")
    assert "Unstable" in markdown(report)


def test_less_accurate_candidate_fails(make_run, fake_workload, fake_server):
    fake_workload.oks = {"a": 1.0, "b": 0.5}
    run = make_run()
    execute(run)
    assert compare(run)["verdict"] == "fail"


def test_a_run_that_did_not_finish_ok_never_passes(make_run, fake_workload, fake_server):
    """A failed second block leaves the surviving rows looking like a pass (council S-01)."""
    fake_workload.speeds = {"a": 50.0, "b": 60.0}
    run = make_run()
    execute(run)
    assert compare(run)["verdict"] == "pass"
    run.finish("failed", missing=40)
    assert compare(run)["verdict"] == "inconclusive"


def test_one_arm_crashing_withholds_only_its_own_verdict(make_run, fake_workload, fake_server, monkeypatch):
    """A tune sweep's crashed arm (OOM at max-num-batched-tokens 8192) left every other arm
    'not finished ok'; the pairs that did not touch it are judged (ledger M32 per pair)."""
    fake_workload.speeds = {"a": 50.0, "b": 60.0, "c": 60.0}
    start = fake_server.start

    def crash_c(self):
        if self.candidate["label"] == "c":
            raise RuntimeError("engine died: out of memory")
        return start(self)
    monkeypatch.setattr(fake_server, "start", crash_c)
    run = make_run(("a", "b", "c"))
    assert execute(run) == 1 and run.done()["failed_labels"] == ["c"]
    assert compare(run, "a", "b")["verdict"] == "pass"
    assert compare(run, "a", "c")["verdict"] == "inconclusive"


def test_errors_in_a_prevent_a_pass(make_run, fake_workload, fake_server, monkeypatch):
    """Half-measured baselines are not evidence for B either."""
    fake_workload.speeds = {"a": 50.0, "b": 60.0}
    original = fake_workload.run_item

    def flaky(ctx, item):
        if ctx.model == "a" and item["id"] == "i3":
            raise RuntimeError("HTTP 500")
        return original(ctx, item)

    monkeypatch.setattr(fake_workload, "run_item", flaky)
    run = make_run()
    execute(run)
    run.finish("ok")  # even if the run were marked finished
    assert compare(run)["verdict"] == "inconclusive"


def test_errors_in_b_fail_even_when_metrics_pass(make_run, fake_workload, fake_server, monkeypatch):
    run = make_run()
    original = fake_workload.run_item

    def flaky(ctx, item):
        if ctx.model == "b" and item["id"] == "i3":
            raise RuntimeError("HTTP 500")
        return original(ctx, item)

    monkeypatch.setattr(fake_workload, "run_item", flaky)
    execute(run)
    assert compare(run)["verdict"] == "fail"


def test_cross_run_label_refused(make_run, fake_workload, fake_server):
    """Baselines from another session are never compared (ledger M13)."""
    run = make_run()
    with pytest.raises(CompareError):
        compare(run, "a", "from-tuesday")


def test_workload_version_change_refused(make_run, fake_workload, fake_server):
    fake_workload.n_items = 2
    run = make_run()
    execute(run)
    fake_workload.VERSION = "2"
    with pytest.raises(CompareError):
        compare(run)


def test_arms_from_two_kernels_are_refused(make_run, fake_workload, fake_server):
    """A reboot between blocks moved b to another kernel (ledger M54)."""
    fake_workload.n_items = 2
    run = make_run()
    execute(run)
    run.write_json("manifest.a.json", {**run.read_json("manifest.a.json"), "kernel": "7.0.0-42-generic"})
    run.write_json("manifest.b.json", {**run.read_json("manifest.b.json"), "kernel": "7.0.0-38-generic"})
    with pytest.raises(CompareError, match="different kernels"):
        compare(run)


def test_single_candidate_gets_only_aa(make_run, fake_workload, fake_server):
    fake_workload.n_items = 5
    run = make_run(labels=("a",))
    execute(run)
    report = compare(run)
    assert report["workloads"]["fake"]["metrics"] == [] and report["workloads"]["fake"]["aa"]
    assert report["verdict"] == "inconclusive"


def test_a_one_block_run_with_reps_reports_rep_aa_and_says_accuracy_is_unmeasured(
        make_run, fake_workload, fake_server):
    """t3 runs each arm once (ab) with reps; its A/A is rep against rep (council S-01/A-02), and a
    tier without LiveCodeBench says it measured no accuracy (council O-02)."""
    run = make_run(design="ab")
    execute(run)
    report = compare(run)
    assert {(x["label"], x["by"]) for x in report["workloads"]["fake"]["aa"]} == {("a", "rep"), ("b", "rep")}
    assert "Accuracy not measured" in markdown(report)


def test_lcb_summary_reports_truncation_and_missing_code():
    """A pass rate alone hid that most failures were truncations (ledger M7)."""
    rows = [{"pass": False, "truncated": True, "no_code": True, "completion_tokens": 16384},
            {"pass": True, "truncated": False, "no_code": False, "completion_tokens": 4000}]
    summary = lcb.summarize(rows)
    assert summary["truncated_rate"] == 0.5 and summary["no_code_rate"] == 0.5
    assert summary["mean_completion_tokens"] == 10192

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


def test_single_candidate_gets_only_aa(make_run, fake_workload, fake_server):
    fake_workload.n_items = 5
    run = make_run(labels=("a",))
    execute(run)
    report = compare(run)
    assert report["workloads"]["fake"]["metrics"] == [] and report["workloads"]["fake"]["aa"]
    assert report["verdict"] == "inconclusive"


def test_lcb_summary_reports_truncation_and_missing_code():
    """A pass rate alone hid that most failures were truncations (ledger M7)."""
    rows = [{"pass": False, "truncated": True, "no_code": True, "completion_tokens": 16384},
            {"pass": True, "truncated": False, "no_code": False, "completion_tokens": 4000}]
    summary = lcb.summarize(rows)
    assert summary["truncated_rate"] == 0.5 and summary["no_code_rate"] == 0.5
    assert summary["mean_completion_tokens"] == 10192

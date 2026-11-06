import pytest

from nevl.store import Run, list_runs


def plan(run_id):
    return {"run_id": run_id, "tier": "t1", "created": 1.0, "candidates": {"a": {}}, "blocks": ["a"]}


def row(item, **extra):
    return {"block": 0, "candidate": "a", "workload": "w", "item": item, "rep": 0, **extra}


def test_done_belongs_to_its_run(tmp_path):
    """A done.json copied from another run is not completion (ledger M4)."""
    run = Run.create(plan("r1"), tmp_path)
    assert run.done() is None
    (run.path / "done.json").write_text('{"run_id": "r0", "status": "ok"}')
    assert run.done() is None
    run.finish("ok")
    assert run.done()["status"] == "ok"
    assert [r["status"] for r in list_runs(tmp_path)] == ["ok"]


def test_torn_line_is_skipped_and_isolated(tmp_path):
    """A lease killed mid-write leaves a partial line; the next row must survive it."""
    run = Run.create(plan("r1"), tmp_path)
    run.append(row("x"))
    with (run.path / "rows.jsonl").open("a") as f:
        f.write('{"block": 0, "cand')
    run.append(row("y"))
    assert sorted(r["item"] for r in run.rows()) == ["x", "y"]


def test_later_row_replaces_earlier_for_the_same_key(tmp_path):
    run = Run.create(plan("r1"), tmp_path)
    run.append(row("x", error="boom"))
    run.append(row("x", score=1))
    assert run.rows() == [row("x", score=1)]


def test_graded_rows_substitute_by_key(tmp_path):
    run = Run.create(plan("r1"), tmp_path)
    run.append(row("x"))
    run.append(row("y"))
    run.write_graded([row("y", graded=True, passed=True)])
    by_item = {r["item"]: r for r in run.graded_rows()}
    assert "graded" not in by_item["x"] and by_item["y"]["passed"]


def test_runs_are_created_once(tmp_path):
    Run.create(plan("r1"), tmp_path)
    with pytest.raises(FileExistsError):
        Run.create(plan("r1"), tmp_path)

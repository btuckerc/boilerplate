import os

import pytest

from nevl.store import Run, boot_time, interrupted, list_runs


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


def test_a_reboot_resumes_only_the_runs_it_cut_short(tmp_path):
    """Started, unfinished, last row in the day before boot (ledger M51)."""
    boot = 1e9
    for name, rows, done, written in (("a-cut", True, False, boot - 600), ("b-cut", True, False, boot - 7200),
                                      ("finished", True, True, boot - 600), ("never-started", False, False, 0),
                                      ("since-boot", True, False, boot + 60), ("last-week", True, False, boot - 7 * 86400)):
        path = tmp_path / "runs" / name
        path.mkdir(parents=True)
        if rows:
            (path / "rows.jsonl").write_text("{}\n")
            os.utime(path / "rows.jsonl", (written, written))
        if done:
            (path / "done.json").write_text("{}")
    assert interrupted(boot, tmp_path) == ["a-cut", "b-cut"]


def test_boot_time_is_read_from_proc_stat(tmp_path):
    (tmp_path / "stat").write_text("cpu  1 2 3\nbtime 1793942340\nprocesses 9\n")
    assert boot_time(tmp_path / "stat") == 1793942340.0

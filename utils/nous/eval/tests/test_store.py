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


def test_graded_rows_substitute_only_the_row_they_graded(tmp_path):
    """A row measured again (its attempt failed the end check) keeps its key; the old grade must
    not stand in for it (ledger M61)."""
    run = Run.create(plan("r1"), tmp_path)
    run.append(row("x", ts=1.0))
    run.append(row("y", ts=1.0))
    run.write_graded([row("y", ts=1.0, graded=True, passed=True)])
    by_item = {r["item"]: r for r in run.graded_rows()}
    assert "graded" not in by_item["x"] and by_item["y"]["passed"]
    run.append(row("y", ts=2.0))
    assert "graded" not in {r["item"]: r for r in run.graded_rows()}["y"]


def test_runs_are_created_once(tmp_path):
    Run.create(plan("r1"), tmp_path)
    with pytest.raises(FileExistsError):
        Run.create(plan("r1"), tmp_path)


def test_a_reboot_resumes_only_the_runs_it_cut_short(tmp_path):
    """Started, unfinished, last row in the day before boot (ledger M51); not one that was
    stopped with SIGTERM by hand or by a clean shutdown (council F-05)."""
    boot = 1e9
    for name, rows, end, written in (("a-cut", True, None, boot - 600), ("b-cut", True, None, boot - 7200),
                                     ("finished", True, "done", boot - 600), ("never-started", False, None, 0),
                                     ("stopped", True, "stopped", boot - 600),
                                     ("since-boot", True, None, boot + 60), ("last-week", True, None, boot - 7 * 86400)):
        path = tmp_path / "runs" / name
        path.mkdir(parents=True)
        if rows:
            (path / "rows.jsonl").write_text("{}\n")
            os.utime(path / "rows.jsonl", (written, written))
        if end:
            (path / f"{end}.json").write_text("{}")
    assert interrupted(boot, tmp_path) == ["a-cut", "b-cut"]


def test_boot_time_is_read_from_proc_stat(tmp_path):
    (tmp_path / "stat").write_text("cpu  1 2 3\nbtime 1793942340\nprocesses 9\n")
    assert boot_time(tmp_path / "stat") == 1793942340.0

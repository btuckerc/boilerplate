#!/usr/bin/env python3
import csv
import datetime as dt
import fcntl
import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "home/dot_local/bin/executable_council-yield"
spec = importlib.util.spec_from_loader("council_yield", SourceFileLoader("council_yield", str(SCRIPT)))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def receipts(tmp_path, monkeypatch):
    home = tmp_path / "runs"
    home.mkdir()
    monkeypatch.setenv("AGENT_RUN_HOME", str(home))
    monkeypatch.setattr(module, "YIELD", tmp_path / "yield.tsv")
    created = []

    def create(name, *, score=9.0, seconds=30, harness="codex", cost=None, state="ok", model=None, effort=None):
        stamp = dt.datetime(2026, 11, 8, 10, tzinfo=dt.timezone.utc) + dt.timedelta(minutes=len(created))
        run = stamp.strftime("%Y%m%dT%H%M%S") + "-ask-" + name
        path = home / run
        path.mkdir()
        meta = {"run": run, "lane": "ask", "model": model or ("claude-fable-5-5" if harness == "claude" else "gpt-6.1-sol"),
                "effort": effort or ("high" if harness == "claude" else "xhigh"), "state": state,
                "started_at": stamp.isoformat(), "ended_at": (stamp + dt.timedelta(seconds=seconds)).isoformat(),
                "child": {"harness": harness}}
        (path / "meta.json").write_text(json.dumps(meta))
        (path / "result.json").write_text(json.dumps({"score": score} if score is not None else {}))
        (path / "events.jsonl").write_text(json.dumps({"total_cost_usd": cost} if cost is not None else {}) + "\n")
        created.append(path)
        return path

    return home, create


def rows():
    with module.YIELD.open(newline="") as src:
        return list(csv.DictReader(src, delimiter="\t"))


def test_bounce_is_same_round_latest_score_and_all_active_time(receipts, capsys):
    home, create = receipts
    create("2026-11-08-demo-sol-r1", score=7.5, seconds=30)
    create("2026-11-08-demo-sol-r1-bounce", score=9.0, seconds=20)
    create("2026-11-08-demo-sol-r3", score=9.5, seconds=40)
    seat = module.read_seat(home, "2026-11-08-demo", "sol")
    assert list(seat["rounds"]) == [1, 3]
    assert seat["rounds"][1] == {"score": 9.0, "seconds": 50.0, "cost": None}
    assert seat["seconds"] == 90
    assert module.main(["add", "2026-11-08-demo", "100", "sol=2/1/3"]) == 0
    out = capsys.readouterr().out
    assert "round 1 | round 3" in out and "round 2" not in out
    assert "9.0 · 0m50s · $?" in out
    assert "gpt-6.1-sol:xhigh" in out
    assert rows()[0] == {"date": "2026-11-08", "slug": "demo", "seat": "sol", "model": "gpt-6.1-sol:xhigh",
                         "lines": "100", "rounds": "2", "alone": "2", "shared": "1", "declined": "3",
                         "cost_usd": "", "active_s": "90"}


def test_claude_costs_sum_bounces_codex_cost_stays_unknown(receipts, capsys):
    _, create = receipts
    create("2026-11-08-demo-sol-r1", cost=999)
    create("2026-11-08-demo-fable-r1", harness="claude", cost=0.12, seconds=15)
    create("2026-11-08-demo-fable-r1-bounce", harness="claude", cost=0.03, score=9.5, seconds=5)
    assert module.main(["add", "2026-11-08-demo", "0", "sol=1/0/0", "fable=0/1/0"]) == 0
    output = capsys.readouterr().out
    assert "9.5 · 0m20s · $0.15" in output
    assert "Total seat cost: $?" in output
    assert [row["cost_usd"] for row in rows()] == ["", "0.15"]
    assert module.main(["summary"]) == 0
    output = capsys.readouterr().out
    assert "| sol | gpt-6.1-sol | 1 | 1 | 1 | 0 | 0.00 | 1 | - |" in output
    assert "| fable | claude-fable-5-5 | 1 | 0 | 1 | 0 | 0.15 | 0 | 0.15 |" in output


def test_missing_claude_cost_does_not_abort_and_dry_run_writes_nothing(receipts, capsys):
    _, create = receipts
    create("2026-11-08-demo-fable-r1", harness="claude")
    assert module.main(["add", "2026-11-08-demo", "0", "fable=0/0/0", "--dry-run"]) == 0
    assert "$?" in capsys.readouterr().out
    assert not module.YIELD.exists()


@pytest.mark.parametrize("state", [None, "running"])
def test_missing_or_still_running_counted_seat_fails_without_rows(receipts, capsys, state):
    _, create = receipts
    create("2026-11-08-demo-fable-r1", harness="claude", cost=0.1)
    if state:
        path = create("2026-11-08-demo-sol-r1", state=state)
        with (path / "runner.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            result = module.main(["add", "2026-11-08-demo", "0", "fable=1/0/0", "sol=0/0/0"])
    else:
        result = module.main(["add", "2026-11-08-demo", "0", "fable=1/0/0", "sol=0/0/0"])
    assert result == 1
    error = capsys.readouterr().err
    assert ("still running" if state else "no agent-run runs") in error
    assert not module.YIELD.exists()


def test_bare_names_report_all_exact_matches_but_append_no_rows(receipts, capsys):
    _, create = receipts
    create("2026-11-08-demo-sol-r1")
    create("2026-11-08-demo-tiebreak-1", harness="claude", cost=0.1, score=None, seconds=10)
    create("2026-11-08-demo-tiebreak-1", harness="claude", cost=0.2, score=None, seconds=20)
    create("other-2026-11-08-demo-tiebreak-1", harness="claude", cost=100, seconds=60)
    assert module.main(["add", "2026-11-08-demo", "0", "sol=0/0/0", "2026-11-08-demo-tiebreak-1"]) == 0
    output = capsys.readouterr().out
    assert "Unscored run 2026-11-08-demo-tiebreak-1 (claude-fable-5-5:high): 0m30s · $0.30" in output
    assert len(rows()) == 1 and rows()[0]["seat"] == "sol"


def test_duplicate_guard_reads_existing_uppercase_seat_rows(receipts, capsys):
    _, create = receipts
    create("2026-11-08-demo-sol-r1")
    with module.YIELD.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=module.HEADER, delimiter="\t")
        writer.writeheader()
        writer.writerow({"date": "2026-11-08", "slug": "demo", "seat": "Sol"})
    original = module.YIELD.read_bytes()
    assert module.main(["add", "2026-11-08-demo", "0", "sol=0/0/0"]) == 1
    assert "already has a row" in capsys.readouterr().err
    assert module.YIELD.read_bytes() == original


def test_summary_sorts_dates_and_keeps_current_model_semantics(receipts, capsys):
    with module.YIELD.open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=module.HEADER, delimiter="\t")
        writer.writeheader()
        for date, model, alone, shared, declined, cost in [
            ("2026-11-08", "gpt-6.1-sol:xhigh", 0, 2, 1, "0.40"),
            ("2026-11-07", "openai-codex/gpt-6.1-sol:xhigh", 2, 0, 1, "0.20"),
            ("2026-11-01", "old-model:xhigh", 99, 0, 0, "99"),
        ]:
            writer.writerow(dict(date=date, slug=date, seat="Sol", model=model, lines="0", rounds="1",
                                 alone=alone, shared=shared, declined=declined, cost_usd=cost, active_s="30"))
    assert module.main(["summary", "--last", "1"]) == 0
    assert "| sol | gpt-6.1-sol | 2 | 0 | 4 | 33 | 0.60 | 0 | 0.15 |" in capsys.readouterr().out


def test_unknown_old_cost_disables_per_verified_even_with_known_recent_cost(receipts, capsys):
    _, create = receipts
    create("2026-11-07-demo-sol-r1")
    assert module.main(["add", "2026-11-07-demo", "0", "sol=1/0/0"]) == 0
    # Existing yield.tsv rows remain readable without any migration.
    with module.YIELD.open("a") as out:
        out.write("2026-11-08\tnew\tsol\tgpt-6.1-sol:xhigh\t0\t1\t1\t0\t0\t0.25\t30\n")
    capsys.readouterr()
    assert module.main(["summary", "--last", "1"]) == 0
    assert "| sol | gpt-6.1-sol | 2 | 1 | 2 | 0 | 0.25 | 1 | - |" in capsys.readouterr().out


@pytest.mark.parametrize("spec", ["architect=1/0/0", "Sol=1/0/0", "sol=wrong", "sol=1/0/0 sol=1/0/0"])
def test_bad_or_duplicate_seat_arguments_are_clear_errors(receipts, capsys, spec):
    _, create = receipts
    create("2026-11-08-demo-sol-r1")
    assert module.main(["add", "2026-11-08-demo", "0", *spec.split()]) == 1
    assert capsys.readouterr().err
    assert not module.YIELD.exists()


def test_rejects_model_changes_instead_of_mislabeling_yield(receipts, capsys):
    _, create = receipts
    create("2026-11-08-demo-sol-r1")
    create("2026-11-08-demo-sol-r2", model="another-model")
    assert module.main(["add", "2026-11-08-demo", "0", "sol=0/0/0"]) == 1
    assert "model/effort changed" in capsys.readouterr().err


def test_same_slug_different_dates_stay_independent(receipts, capsys):
    _, create = receipts
    create("2026-11-01-x-fable-r1", harness="claude", cost=0.1, seconds=10)
    create("2026-11-08-x-fable-r1", harness="claude", cost=0.2, seconds=20)
    create("2026-11-08-x-fable-r2", harness="claude", cost=0.3, seconds=30)
    assert module.main(["add", "2026-11-01-x", "0", "fable=1/0/0"]) == 0
    assert module.main(["add", "2026-11-08-x", "0", "fable=1/0/0"]) == 0
    assert [(r["rounds"], r["cost_usd"], r["active_s"]) for r in rows()] == [
        ("1", "0.10", "10"), ("2", "0.50", "50")]


def test_yield_settles_orphaned_run(receipts):
    _, create = receipts
    path = create("2026-11-08-demo-fable-r1", harness="claude", state="running")
    meta = json.loads((path / "meta.json").read_text())
    meta["started_at"] = "2026-11-01T10:00:00+00:00"
    (path / "meta.json").write_text(json.dumps(meta))
    assert module.main(["add", "2026-11-08-demo", "0", "fable=0/0/0"]) == 0
    assert json.loads((path / "meta.json").read_text())["state"] == "abandoned"

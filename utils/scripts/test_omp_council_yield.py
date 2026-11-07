#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "home/dot_local/bin/executable_omp-council-yield"
spec = importlib.util.spec_from_loader("council_yield", SourceFileLoader("council_yield", str(SCRIPT)))
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

RUN = "2026-11-07-demo"


def header(agent="architect", model="openai-codex/gpt-6.1-sol", effort="xhigh"):
    return [
        {"type": "session_init", "agent": agent},
        {"type": "model_change", "model": model},
        {"type": "thinking_level_change", "thinkingLevel": effort},
        {"type": "message", "timestamp": "2026-11-07T10:00:00Z", "message": {"role": "user", "content": []}},
    ]


def director(stamp, text):
    return {"type": "custom_message", "customType": "irc:incoming", "timestamp": stamp,
            "content": f"<irc>\nIncoming IRC message from agent `Main`:\n\n{text}\n</irc>",
            "details": {"from": "Main", "message": text}}


def turn(stamp, cost=0.0, data=None):
    content = [{"type": "toolCall", "name": "yield", "arguments": {"data": data}}] if data is not None else []
    return {"type": "message", "timestamp": stamp,
            "message": {"role": "assistant", "content": content, "usage": {"cost": {"total": cost}}}}


class CouncilYieldTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.session = Path(tmp.name) / "session"
        self.session.mkdir()
        self.yield_file = Path(tmp.name) / "yield.tsv"
        self.addCleanup(setattr, module, "YIELD", module.YIELD)
        module.YIELD = self.yield_file

    def write(self, ident, entries):
        (self.session / f"{ident}.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main([*argv[:1], RUN, *argv[1:], "--session-dir", str(self.session)] if argv[0] == "add" else list(argv))
        return code, out.getvalue(), err.getvalue()

    def rows(self):
        lines = self.yield_file.read_text().splitlines()
        return [dict(zip(lines[0].split("\t"), line.split("\t"))) for line in lines[1:]]

    def test_a_bounce_stays_in_its_round_and_a_skipped_round_stays_empty(self):
        self.write("S1", header() + [
            turn("2026-11-07T10:01:00Z", 0.5), turn("2026-11-07T10:02:00Z", data={"score": 9.4}),
            director("2026-11-07T10:30:00Z", "Round 2. Your score 9.4 is outside the band of S-01 (should)."),
            turn("2026-11-07T10:30:30Z", 0.1, data={"score": 8.4}),
            director("2026-11-07T11:00:00Z", "Council seat, round 3. Tree abc in run/tree-r3."),
            turn("2026-11-07T11:01:00Z", 0.2, data={"score": 9.0}),
            {"type": "model_usage", "usage": {"cost": {"total": 0.05}}},
        ])
        self.write("F1", header("fable", "anthropic/claude-fable-5-1", "medium") + [
            turn("2026-11-07T10:03:00Z", 1.0, data={"score": 7.0}),
            director("2026-11-07T10:40:00Z", "Council seat, round 2. Tree def in run/tree-r2."),
            turn("2026-11-07T10:41:00Z", 0.4, data={"score": 8.0}),
        ])
        code, out, _ = self.run_cli("add", "120", "S1=2/3/1", "F1=1/0/0")
        self.assertEqual(code, 0)
        self.assertIn("| seat | agent | round 1 | round 2 | round 3 | total |", out)
        self.assertIn("| sol | S1 | 8.4 · 2m30s · $0.60 |  | 9.0 · 1m00s · $0.25 | 3m30s · $0.85 |", out)
        self.assertIn("| fable | F1 | 7.0 · 3m00s · $1.00 | 8.0 · 1m00s · $0.40 |  | 4m00s · $1.40 |", out)
        self.assertIn("S1: 1 director message(s) without a round line folded into the current round", out)
        self.assertNotIn("F1:", out)
        sol = self.rows()[0]
        self.assertEqual(
            (sol["date"], sol["slug"], sol["seat"], sol["model"], sol["lines"], sol["rounds"], sol["alone"], sol["shared"], sol["declined"], sol["cost_usd"], sol["active_s"]),
            ("2026-11-07", "demo", "sol", "openai-codex/gpt-6.1-sol:xhigh", "120", "2", "2", "3", "1", "0.85", "210"),
        )

    def test_any_unknown_cost_appends_nothing(self):
        good = header() + [turn("2026-11-07T10:01:00Z", 0.1)]
        no_usage = turn("2026-11-07T10:02:00Z")
        del no_usage["message"]["usage"]
        no_total = turn("2026-11-07T10:02:00Z")
        no_total["message"]["usage"] = {"cost": {}}
        probe = {"type": "model_usage", "usage": {"input": 5}}
        for entries in (good + [no_usage], good + [no_total], good + [probe], good[:3] + [probe] + good[3:]):
            self.write("S1", entries)
            code, _, err = self.run_cli("add", "10", "S1=1/0/0")
            self.assertEqual(code, 1)
            self.assertIn("cost unknown", err)
            self.assertFalse(self.yield_file.exists())

    def test_bare_ids_are_reported_not_counted_and_a_repeat_run_is_refused(self):
        self.write("S1", header() + [turn("2026-11-07T10:01:00Z", 0.1, data={"score": 9.0})])
        self.write("T1", header("opus", "anthropic/claude-opus-5-5", "high") + [turn("2026-11-07T10:01:00Z", 0.2, data="prose ruling")])
        code, out, _ = self.run_cli("add", "10", "S1=1/0/0", "T1")
        self.assertEqual(code, 0)
        self.assertIn("Unscored agent T1 (opus): 1m00s · $0.20", out)
        self.assertIn("Total seat cost: $0.30", out)
        self.assertEqual([r["seat"] for r in self.rows()], ["sol"])
        code, _, err = self.run_cli("add", "10", "S1=1/0/0")
        self.assertEqual(code, 1)
        self.assertIn("already has a row", err)
        self.assertEqual(len(self.rows()), 1)

    def test_summary_uses_run_dates_not_append_order_and_only_the_current_model(self):
        head = "\t".join(module.HEADER)
        old = "2026-11-01\ta\tSol\tgpt-6-sol:xhigh\t10\t1\t9\t0\t0\t1.00\t10"
        mixed = "2026-11-05\tb\tSol\tgpt-6.1-sol:xhigh\t10\t1\t1\t1\t2\t0.40\t10"
        new = "2026-11-06\tc\tsol\topenai-codex/gpt-6.1-sol:xhigh\t10\t1\t0\t2\t0\t0.20\t10"
        self.yield_file.write_text("\n".join([head, mixed, new, old]) + "\n")
        code, out, _ = self.run_cli("summary", "--last", "1")
        self.assertEqual(code, 0)
        self.assertIn("| sol | gpt-6.1-sol | 2 | 0 | 4 | 33 | 0.60 | 0.15 |", out)


if __name__ == "__main__":
    unittest.main()

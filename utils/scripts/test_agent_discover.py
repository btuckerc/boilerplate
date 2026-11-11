#!/usr/bin/env python3
"""agent-discover: estimator checked against the 2026-11-11 fleet-ssh v1 experiment.

Three independent exhaustive Sol reviewers of fleet-ssh v1 (2d3d8d6); findings
merged by root cause into IDs. Recorded result: 55 distinct defects, f1=16,
f2=10, Chao and jackknife both ~66 total.
"""
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import contextlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "home/dot_local/bin/executable_agent-discover"
spec = importlib.util.spec_from_loader("agent_discover", SourceFileLoader("agent_discover", str(SCRIPT)))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FLEET_SSH_V1 = {"r1": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20", "C21", "C22", "C23", "C24", "C25", "C26", "C27", "C28", "C29", "C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37"], "r2": ["C1", "C2", "C26", "C20", "C15", "C16", "C14", "C3", "C39", "C5", "C4", "C6", "C12", "C38", "C9", "C36", "C31", "C13", "C17", "C11", "C30", "C23", "C40", "C41", "C42", "C24", "C27", "C33", "C21", "C22", "C35", "C37", "C43", "C34", "C18", "C19", "C44", "C28", "C45", "C46", "C47", "C48"], "r3": ["C26", "C24", "C1", "C2", "C5", "C4", "C39", "C3", "C6", "C7", "C49", "C12", "C38", "C9", "C13", "C50", "C15", "C16", "C14", "C20", "C21", "C22", "C27", "C33", "C30", "C17", "C11", "C23", "C28", "C43", "C35", "C37", "C36", "C31", "C51", "C19", "C52", "C44", "C34", "C53", "C40", "C41", "C54", "C47", "C55"]}


class EstimateTest(unittest.TestCase):
    def test_fleet_ssh_v1_experiment(self):
        r = module.estimate(FLEET_SSH_V1)
        self.assertEqual((r["found"], r["found_by_one"], r["found_by_two"]), (55, 16, 10))
        self.assertAlmostEqual(r["estimate_chao"], 65.9)
        self.assertAlmostEqual(r["estimate_jackknife"], 65.7)

    def test_full_overlap_means_nothing_left(self):
        r = module.estimate({"a": ["x", "y"], "b": ["y", "x"], "c": ["x", "y"]})
        self.assertEqual((r["remaining_chao"], r["remaining_jackknife"]), (0, 0))

    def test_duplicates_within_a_reviewer_count_once(self):
        r = module.estimate({"a": ["x", "x"], "b": ["x"]})
        self.assertEqual(r["found_by_one"], 0)

    def test_one_reviewer_is_refused(self):
        with self.assertRaises(ValueError):
            module.estimate({"a": ["x"]})

    def test_cli(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(module.main(["schema"]), 0)
        self.assertIn("findings", json.loads(out.getvalue())["properties"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(module.main(["brief"]), 0)
        self.assertIn("EVERY defect", out.getvalue())


if __name__ == "__main__":
    unittest.main()

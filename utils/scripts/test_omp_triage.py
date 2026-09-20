#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "home/dot_local/bin/executable_omp-triage"
spec = importlib.util.spec_from_loader("omp_triage", SourceFileLoader("omp_triage", str(SCRIPT)))
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def opener_factory(payload, seen):
    def opener(req, timeout):
        seen.append((req, timeout, json.loads(req.data)))
        return Response(payload)
    return opener


class TriageTests(unittest.TestCase):
    def payload(self, choice=module.LABELS[1], confidence=0.87, probabilities=None, cost=0.0002685):
        return {"answers": {"route": {"choice": choice, "confidence": confidence, "probabilities": probabilities or {x: 0.1 for x in module.LABELS}}}, "usage": {"cost": cost}}

    def test_valid_case_preserves_confidence_and_sends_only_request(self):
        probs = {x: (0.8 if x == module.LABELS[1] else 0.0666666667) for x in module.LABELS}
        seen = []
        result = module.triage("fix the failing parser tests", "secret", opener_factory(self.payload(probabilities=probs), seen))
        self.assertEqual(result["choice"], module.LABELS[1])
        self.assertEqual(result["confidence"], 0.87)
        self.assertEqual(result["probabilities"], probs)
        self.assertEqual(result["cost"], 0.0002685)
        self.assertGreaterEqual(result["elapsed_ms"], 0)
        self.assertEqual(seen[0][1], 5)
        self.assertEqual(seen[0][2]["state"], {"request": "fix the failing parser tests"})
        self.assertNotIn("secret", json.dumps(seen[0][2]))
        self.assertEqual(seen[0][0].get_header("Authorization"), "Bearer secret")

    def test_malformed_and_unknown_choice_rejected(self):
        for payload in ({}, {"answers": {"route": {"choice": "cloud", "confidence": 1, "probabilities": {}}}}):
            with self.assertRaises((RuntimeError, ValueError)):
                module._response(payload, 1)

    def test_invalid_numeric_answers_rejected(self):
        for value in (float("nan"), 1.1, -0.1, "0.5"):
            with self.assertRaises(ValueError):
                module._response(self.payload(confidence=value), 1)

    def test_request_bound_and_stdin(self):
        env = os.environ.copy()
        env["OPENROUTER_API_KEY"] = "dummy"
        too_long = subprocess.run([str(SCRIPT), "x" * (module.MAX_REQUEST_CHARS + 1)], env=env, text=True, capture_output=True)
        self.assertNotEqual(too_long.returncode, 0)
        self.assertIn("exceeds", too_long.stderr)

    def test_stdin_request_is_forwarded_without_live_call(self):
        original_key, original_triage, original_stdin = module._key, module.triage, sys.stdin
        try:
            module._key = lambda: "key"
            seen = []
            module.triage = lambda request, key: seen.append((request, key)) or {
                "choice": module.LABELS[0], "confidence": 1.0, "probabilities": {}, "elapsed_ms": 0, "cost": 0.0
            }
            sys.stdin = io.StringIO("extract the version")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(module.main([]), 0)
            self.assertEqual(seen, [("extract the version", "key")])
            self.assertIn('"choice":"local"', output.getvalue())
        finally:
            module._key, module.triage, sys.stdin = original_key, original_triage, original_stdin

    def test_errors_do_not_print_auth_or_provider_body(self):
        class Failing:
            def __call__(self, req, timeout):
                raise module.urllib.error.HTTPError(req.full_url, 401, "bad", {}, io.BytesIO(b"Bearer secret provider body"))
        with self.assertRaises(RuntimeError):
            module.triage("request", "Bearer secret", Failing())
        env = os.environ.copy()
        env.pop("OPENROUTER_API_KEY", None)
        with tempfile.TemporaryDirectory() as home:
            env["HOME"] = home
            result = subprocess.run([str(SCRIPT), "request"], env=env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("omp-openrouter-env", result.stderr)
        self.assertNotIn("secret-value", result.stderr)
        self.assertNotIn("provider body", result.stderr)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Check appliance monitoring without deploying software or loading models."""
import io
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "home/dot_local/bin/executable_decent-angl-doctor"
report = runpy.run_path(str(SCRIPT))["inference_report"]
HOST = {"id": "nous", "ssh": "tux@nous", "inference_endpoints": {
    "llama.service": "http://nous:8080", "bonsai.service": "http://nous:8081"}}


class InferenceDoctorTest(unittest.TestCase):
    def probe(self, states, responses):
        calls = []
        def fetch(url, timeout):
            calls.append(url)
            return io.BytesIO(json.dumps(responses[len(calls)-1]).encode())
        with patch.dict(report.__globals__, run=lambda *a, **kw: (0, "Linux\n" + states + "\nGPU\n")):
            with patch("urllib.request.urlopen", side_effect=fetch):
                result = report(HOST)
        return result, calls

    def test_both_backend_selections(self):
        for states, port in (("active\ninactive", 8080), ("inactive\nactive", 8081)):
            result, calls = self.probe(states, [{"status": "ok"}, {"data": [{"id": "model"}]}])
            self.assertEqual(result["issues"], [])
            self.assertEqual(calls, [f"http://nous:{port}/health", f"http://nous:{port}/v1/models"])

    def test_no_backend_does_not_call_api(self):
        result, calls = self.probe("inactive\ninactive", [])
        self.assertTrue(result["issues"])
        self.assertEqual(calls, [])

    def test_bad_inventory_is_reported(self):
        result, _ = self.probe("active\ninactive", [{"status": "ok"}, {"wrong": []}])
        self.assertTrue(result["issues"])

    def test_ssh_failure(self):
        with patch.dict(report.__globals__, run=lambda *a, **kw: (255, "")):
            with patch("urllib.request.urlopen") as fetch:
                result = report(HOST)
        self.assertFalse(result["ssh_ok"])
        self.assertTrue(result["issues"])
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest.mock import patch
import measure

class NativeCaptureTests(unittest.TestCase):
    def test_component_split_uses_actual_openai_shape(self):
        req = {"model": "capture", "messages": [{"role": "system", "content": "policy"}, {"role": "user", "content": "task"}], "tools": [{"type": "function", "function": {"name": "read"}}]}
        system, tools, wire = measure._components(req)
        self.assertEqual(system, "policy"); self.assertIn('"name":"read"', tools); self.assertEqual(json.loads(wire)["model"], "capture")

    def test_remote_mode_fails_closed(self):
        with patch.object(measure, "_capture", return_value=([{"model": "capture", "messages": [], "tools": []}], {})), patch.object(measure, "_remote_counts", return_value=(None, "remote-unavailable:test")):
            with self.assertRaises(RuntimeError): measure.measure("remote")

    def test_profiles_are_explicit_native_cases(self):
        self.assertEqual(set(measure.PROFILES), {"isolated-xdev-catalog-no-discovery", "isolated-xdev-disabled-no-discovery", "baseline-six-file-tools", "candidate-three-tools-approximation", "scoped-read-edit-write-bash"})
        self.assertEqual(measure.PROFILES["baseline-six-file-tools"]["tools"], "read,grep,glob,edit,write,yield")
        self.assertEqual(measure.PROFILES["candidate-three-tools-approximation"]["tools"], "read,write,yield")

if __name__ == "__main__": unittest.main()

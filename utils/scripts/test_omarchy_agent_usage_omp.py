#!/usr/bin/env python3
"""Focused contract checks for the native Codex usage collector."""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


COLLECTOR = Path(__file__).parents[2] / "home" / "dot_local" / "bin" / "executable_omarchy-agent-usage-omp"
LOADER = importlib.machinery.SourceFileLoader("omarchy_agent_usage_omp", str(COLLECTOR))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
collector = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(collector)


def test_scan_filters_to_codex() -> None:
  with tempfile.TemporaryDirectory() as temp:
    sessions = Path(temp) / "sessions"
    sessions.mkdir()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    records = [
      {
        "type": "message",
        "id": "codex-message",
        "timestamp": now,
        "message": {
          "role": "assistant",
          "provider": "openai-codex",
          "model": "gpt-5-codex",
          "usage": {"input": 10, "output": 5},
        },
      },
      {
        "type": "message",
        "id": "other-message",
        "timestamp": now,
        "message": {
          "role": "assistant",
          "provider": "other-provider",
          "model": "other-model",
          "usage": {"input": 100, "output": 50},
        },
      },
    ]
    (sessions / "one.jsonl").write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    with patch.object(collector, "session_roots", return_value=[sessions]):
      stats = collector.scan_sessions()
    assert stats["totalPrompts"] == 1
    assert stats["todayTotalTokens"] == 15
    assert stats["modelUsage"]["gpt-5-codex"]["inputTokens"] == 10
    assert "other-model" not in stats["modelUsage"]


def test_limits_filter_to_codex() -> None:
  limits, tier = collector.limits_from_payload({
    "reports": [
      {"provider": "openai-codex", "limits": [{
        "label": "5h",
        "amount": {"usedFraction": 0.25},
        "window": {"resetsAt": 1_800_000_000_000},
      }]},
      {"provider": "other-provider", "limits": [{
        "label": "other-limit",
        "amount": {"usedFraction": 0.9},
      }]},
    ],
  })
  assert tier == "Codex"
  assert len(limits) == 1
  assert limits[0]["percent"] == 0.25


if __name__ == "__main__":
  test_scan_filters_to_codex()
  test_limits_filter_to_codex()
  print("OMP Codex collector tests passed")

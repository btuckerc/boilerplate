#!/usr/bin/env python3
"""Focused contract checks for the OpenRouter usage collector."""

from __future__ import annotations

import datetime as dt
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


COLLECTOR = Path(__file__).parents[2] / "home" / "dot_local" / "bin" / "executable_omarchy-agent-usage-openrouter"
LOADER = importlib.machinery.SourceFileLoader("omarchy_agent_usage_openrouter", str(COLLECTOR))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
collector = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(collector)


def test_scan_filters_provider() -> None:
  with tempfile.TemporaryDirectory() as temp:
    sessions = Path(temp) / "sessions"
    sessions.mkdir()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    records = [
      {
        "type": "message",
        "id": "openrouter-message",
        "timestamp": now,
        "message": {
          "role": "assistant",
          "provider": "openrouter",
          "model": "openai/gpt-4o-mini",
          "usage": {"input": 10, "output": 5},
        },
      },
      {
        "type": "message",
        "id": "xai-message",
        "timestamp": now,
        "message": {
          "role": "assistant",
          "provider": "xai-oauth",
          "model": "grok-4.6",
          "usage": {"input": 100, "output": 50},
        },
      },
    ]
    (sessions / "one.jsonl").write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
    with patch.object(collector, "session_roots", return_value=[sessions]):
      stats = collector.scan_sessions()
    assert stats["totalPrompts"] == 1
    assert stats["totalSessions"] == 1
    assert stats["todayTotalTokens"] == 15
    assert stats["modelUsage"]["openai/gpt-4o-mini"]["inputTokens"] == 10
    assert "grok-4.6" not in stats["modelUsage"]


def test_balance_fixture() -> None:
  balance = collector.balance_from_payload({"data": {"total_credits": 100, "total_usage": 25}})
  assert balance == {
    "remaining": 75.0,
    "currency": "USD",
    "estimated": False,
  }


def test_key_cap_fixture() -> None:
  balance = collector.key_balance_from_payload({"data": {"limit": 40, "usage": 7}})
  assert balance == {
    "remaining": 33.0,
    "funded": 40.0,
    "spent": 7.0,
    "currency": "USD",
    "estimated": False,
  }
  remaining = collector.key_balance_from_payload({"data": {"limit": 40, "usage": 7, "limit_remaining": 31}})
  assert remaining is not None
  assert remaining["remaining"] == 31.0



def test_main_never_prints_key() -> None:
  fake_key = "fake-key-that-must-not-be-printed"
  with tempfile.TemporaryDirectory() as temp:
    sessions = Path(temp) / "sessions"
    sessions.mkdir()
    cache = Path(temp) / "cache"
    with patch.dict(os.environ, {"XDG_CACHE_HOME": str(cache), "OPENROUTER_API_KEY": fake_key}, clear=False), \
         patch.object(collector, "session_roots", return_value=[sessions]), \
         patch.object(collector, "api_get", side_effect=[
           {"data": {"total_credits": 100, "total_usage": 25}},
           {"data": {"limit": None}},
         ]), \
         patch.object(sys, "argv", [str(COLLECTOR), "--force", "--api-base-url", "https://fixture.invalid/api/v1"]):
      output = io.StringIO()
      with contextlib.redirect_stdout(output):
        assert collector.main() == 0
    record = json.loads(output.getvalue())
    assert record["id"] == "openrouter"
    assert record["balance"]["remaining"] == 75.0
    assert "funded" not in record["balance"]
    assert "spent" not in record["balance"]
    assert "limits" not in record
    assert record["ready"] is True
    assert fake_key not in output.getvalue()


def main() -> int:
  test_scan_filters_provider()
  test_balance_fixture()
  test_key_cap_fixture()
  test_main_never_prints_key()
  print("OpenRouter collector tests passed")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

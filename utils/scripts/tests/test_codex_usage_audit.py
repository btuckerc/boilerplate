import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "codex_usage_audit.py"
spec = importlib.util.spec_from_file_location("codex_usage_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit)


def _write(tmp_path, records, tail=""):
    sessions = tmp_path / "sessions" / "nested"
    sessions.mkdir(parents=True)
    path = sessions / "rollout.jsonl"
    path.write_text("".join(json.dumps(item) + "\n" for item in records) + tail, encoding="utf-8")
    return tmp_path


def _record(kind, timestamp, response_id=None, **payload):
    if response_id is not None:
        payload["response_id"] = response_id
    return {"type": kind, "timestamp": timestamp, "payload": payload}


def test_dedupes_rollouts_and_cache_is_input_subset(tmp_path):
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    stamp = now.isoformat()
    records = [
        _record("turn_context", (now - timedelta(days=20)).isoformat(), model="gpt-5", effort="high"),
        _record("token_usage_record", stamp, "r1", usage={"input_tokens": 200_000, "cached_input_tokens": 150_000, "output_tokens": 100, "reasoning_tokens": 40}),
        _record("token_usage_record", stamp, "r1", usage={"input_tokens": 200_000, "cached_input_tokens": 150_000, "output_tokens": 100, "reasoning_tokens": 40}),
        _record("token_usage_record", stamp, "r2", model="gpt-5", usage={"input_tokens": 4, "cached_input_tokens": 9, "output_tokens": 8, "reasoning_tokens": 3}),
    ]
    report = audit.scan([_write(tmp_path, records)], days=14, now=now)
    model = report["models"]["gpt-5"]
    assert model["response_count"] == 2
    assert model["input_tokens"] == 200004
    assert model["cached_input_tokens"] == 150004
    assert model["uncached_input_tokens"] == 50000
    assert model["reasoning_tokens"] == 43
    assert model["input_context"] == {"p50": 4, "p90": 200000, "max": 200000, "count_above_128k": 1}
    assert report["totals"]["reasoning_is_subset_of_output"] is True


def test_date_filter_coverage_compaction_and_malformed_tail(tmp_path):
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    old = (now - timedelta(days=20)).isoformat()
    current = now.isoformat()
    records = [
        _record("response", current, "missing", model="gpt-5"),
        _record("compaction", current),
        _record("token_usage_record", current, "current", usage={"input_tokens": 10, "output_tokens": 5}),
        _record("token_usage_record", old, "old", usage={"input_tokens": 900, "output_tokens": 9}),
    ]
    report = audit.scan([_write(tmp_path, records, tail='{"type":"token_usage_record"')], days=14, now=now)
    assert report["totals"]["response_count"] == 1
    assert report["coverage"]["response_ids_observed"] == 2
    assert report["coverage"]["usage_records"] == 1
    assert report["coverage"]["missing_usage_records"] == 1
    assert report["compaction_events"] == 1
    assert report["malformed_lines"] == 1


def test_legacy_cumulative_counter_is_coverage_only(tmp_path):
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    legacy = {"type": "event_msg", "timestamp": now.isoformat(), "payload": {"type": "token_count", "info": {"total_token_usage": 999999}}}
    covered = tmp_path / "covered"
    missing = tmp_path / "missing"
    _write(covered, [legacy, legacy, _record("token_usage_record", now.isoformat(), "covered", usage={"input_tokens": 1, "output_tokens": 1})])
    _write(missing, [legacy, legacy])
    report = audit.scan([covered, missing], now=now)
    assert report["totals"]["response_count"] == 1
    assert report["coverage"]["legacy_files_without_usage_records"] == 1


def test_duplicate_response_across_files_and_reasoning_alias(tmp_path):
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    stamp = now.isoformat()
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write(first, [_record("token_usage_record", stamp, "same", model="gpt-5", usage={"input_tokens": 10, "output_tokens": 8, "reasoning_output_tokens": 7})])
    _write(second, [_record("token_usage_record", stamp, "same", model="gpt-5", usage={"input_tokens": 10, "output_tokens": 8, "reasoning_output_tokens": 7})])
    report = audit.scan([first, second], now=now)
    assert report["totals"]["response_count"] == 1
    assert report["totals"]["reasoning_tokens"] == 7


def test_archived_rollouts_are_scanned_and_deduped(tmp_path):
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    record = _record("token_usage_record", now.isoformat(), "archived-id", model="gpt-5", usage={"input_tokens": 12, "output_tokens": 4})
    sessions = tmp_path / "sessions"
    archived = tmp_path / "archived_sessions" / "nested"
    sessions.mkdir()
    archived.mkdir(parents=True)
    encoded = json.dumps(record) + "\n"
    (sessions / "current.jsonl").write_text(encoded, encoding="utf-8")
    (archived / "archived.jsonl").write_text(encoded, encoding="utf-8")
    report = audit.scan([tmp_path], now=now)
    assert report["source_files"] == 2
    assert report["totals"]["response_count"] == 1


def test_model_source_ambiguity_is_reported(tmp_path):
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    stamp = now.isoformat()
    records = [_record("token_usage_record", stamp, "unknown", usage={"input_tokens": 1, "output_tokens": 1})]
    report = audit.scan([_write(tmp_path, records)], now=now)
    assert report["source_counts"]["model"] == {"unknown": 1}
    assert report["models"]["unknown"]["effort_counts"] == {"unknown": 1}

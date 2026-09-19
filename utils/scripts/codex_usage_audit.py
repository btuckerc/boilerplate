#!/usr/bin/env python3
"""Read-only aggregate audit of recent Codex session usage records.

The scanner deliberately consumes only token metadata and never emits session
or message contents.  It is tolerant of a log currently being appended to.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable


def _number(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _timestamp(value: Any) -> _dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=_dt.timezone.utc)).astimezone(_dt.timezone.utc)
    except ValueError:
        return None


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("payload")
    return value if isinstance(value, dict) else {}


def _field(record: dict[str, Any], payload: dict[str, Any], *names: str) -> Any:
    for source in (payload, record):
        for name in names:
            if name in source and source[name] is not None:
                return source[name]
    return None


def _usage(payload: dict[str, Any]) -> dict[str, int] | None:
    value = payload.get("usage")
    if not isinstance(value, dict):
        return None
    # OpenAI style names are preferred, with compact names accepted for older logs.
    return {
        "input": _number(value.get("input_tokens", value.get("input"))),
        "cached": _number(value.get("cached_input_tokens", value.get("cache_read_input_tokens", value.get("cached_input", value.get("cached"))))),
        "output": _number(value.get("output_tokens", value.get("output"))),
        "reasoning": _number(value.get("reasoning_output_tokens", value.get("reasoning_tokens", value.get("reasoning")))),
    }


def _percentile(values: list[int], fraction: float) -> int | None:
    if not values:
        return None
    return values[max(0, math.ceil(len(values) * fraction) - 1)]


def default_homes() -> list[Path]:
    home = Path.home()
    result = [home / ".codex"]
    for parent_name in (".codex-t3", ".codex-gui"):
        parent = home / parent_name
        if parent.is_dir():
            result.extend(sorted(child for child in parent.iterdir() if child.is_dir()))
    return result


def _session_files(homes: Iterable[Path]) -> list[Path]:
    found: set[Path] = set()
    for home in homes:
        root = Path(home).expanduser()
        if not root.exists():
            continue
        for directory in ("sessions", "archived_sessions"):
            for path in root.glob(f"{directory}/**/*.jsonl"):
                if path.is_file():
                    found.add(path.resolve())
    return sorted(found)


def scan(homes: Iterable[Path], days: int = 14, now: _dt.datetime | None = None) -> dict[str, Any]:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    cutoff = now - _dt.timedelta(days=max(0, days))
    responses: dict[str, dict[str, Any]] = {}
    observed: set[str] = set()
    usage_ids: set[str] = set()
    malformed = 0
    compactions = 0
    source_files = 0
    legacy_files: set[Path] = set()
    usage_files: set[Path] = set()

    for filename in _session_files(homes):
        source_files += 1
        context: dict[str, Any] = {}
        try:
            stream = filename.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    malformed += 1
                    continue
                if not isinstance(record, dict):
                    continue
                timestamp = _timestamp(record.get("timestamp") or record.get("created_at") or _payload(record).get("timestamp"))
                if timestamp is None or timestamp > now:
                    continue
                in_window = timestamp >= cutoff
                payload = _payload(record)
                kind = str(record.get("type") or payload.get("type") or "")
                response_id = _field(record, payload, "response_id", "responseId")
                if in_window and isinstance(response_id, str) and response_id:
                    observed.add(response_id)
                if in_window and ("compact" in kind.lower() or "compaction" in str(payload.get("event_type", "")).lower()):
                    compactions += 1

                model = _field(record, payload, "model")
                effort = _field(record, payload, "effort", "reasoning_effort")
                turn_context = payload.get("turn_context")
                if isinstance(turn_context, dict):
                    model = model or turn_context.get("model")
                    effort = effort or turn_context.get("effort") or turn_context.get("reasoning_effort")
                if model is not None or effort is not None or "turn_context" in kind.lower():
                    if model is not None:
                        context["model"] = str(model)
                    if effort is not None:
                        context["effort"] = str(effort)
                if not in_window:
                    continue

                usage = _usage(payload)
                if "token_usage_record" not in kind.lower() or usage is None or not isinstance(response_id, str) or not response_id:
                    if payload.get("type") == "token_count":
                        legacy_files.add(filename)
                    continue
                usage_ids.add(response_id)
                usage_files.add(filename)
                if response_id in responses:
                    continue
                # A usage record can carry authoritative model/effort metadata.
                usage_model = _field(record, payload, "model")
                usage_effort = _field(record, payload, "effort", "reasoning_effort")
                responses[response_id] = {
                    "usage": usage,
                    "model": str(usage_model) if usage_model is not None else context.get("model", "unknown"),
                    "effort": str(usage_effort) if usage_effort is not None else context.get("effort", "unknown"),
                    "model_source": "usage_record" if usage_model is not None else ("turn_context" if context.get("model") else "unknown"),
                    "effort_source": "usage_record" if usage_effort is not None else ("turn_context" if context.get("effort") else "unknown"),
                }

    models: dict[str, dict[str, Any]] = {}
    model_sources: dict[str, int] = {}
    effort_sources: dict[str, int] = {}
    for item in responses.values():
        model = item["model"]
        stats = models.setdefault(model, {"response_count": 0, "input_tokens": 0, "cached_input_tokens": 0, "uncached_input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "input_context": {"p50": None, "p90": None, "max": None, "count_above_128k": 0}, "effort_counts": {}})
        usage = item["usage"]
        stats["response_count"] += 1
        stats["input_tokens"] += usage["input"]
        stats["cached_input_tokens"] += min(usage["cached"], usage["input"])
        stats["uncached_input_tokens"] += max(0, usage["input"] - usage["cached"])
        stats["output_tokens"] += usage["output"]
        stats["reasoning_tokens"] += usage["reasoning"]
        stats.setdefault("_contexts", []).append(usage["input"])
        stats["effort_counts"][item["effort"]] = stats["effort_counts"].get(item["effort"], 0) + 1
        model_sources[item["model_source"]] = model_sources.get(item["model_source"], 0) + 1
        effort_sources[item["effort_source"]] = effort_sources.get(item["effort_source"], 0) + 1
    for stats in models.values():
        values = sorted(stats.pop("_contexts"))
        stats["input_context"] = {"p50": _percentile(values, .50), "p90": _percentile(values, .90), "max": max(values) if values else None, "count_above_128k": sum(value > 128_000 for value in values)}

    legacy_without_usage = len(legacy_files - usage_files)
    totals = {
        "response_count": len(responses),
        "input_tokens": sum(x["usage"]["input"] for x in responses.values()),
        "cached_input_tokens": sum(min(x["usage"]["cached"], x["usage"]["input"]) for x in responses.values()),
        "output_tokens": sum(x["usage"]["output"] for x in responses.values()),
        "reasoning_tokens": sum(x["usage"]["reasoning"] for x in responses.values()),
        "reasoning_is_subset_of_output": True,
    }
    coverage = {
        "response_ids_observed": len(observed),
        "usage_records": len(usage_ids),
        "missing_usage_records": max(0, len(observed - usage_ids)),
        "legacy_files_without_usage_records": legacy_without_usage,
        "limitation": "missing coverage counts only in-window records with a response_id; records without one cannot be matched",
    }
    return {
        "generated_at": now.isoformat(),
        "days": days,
        "cutoff": cutoff.isoformat(),
        "source_files": source_files,
        "models": models,
        "totals": totals,
        "coverage": coverage,
        "source_counts": {"model": model_sources, "effort": effort_sources},
        "compaction_events": compactions,
        "compaction_events_note": "observed log events; forked histories may duplicate a logical compaction",
        "malformed_lines": malformed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--home", action="append", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.days < 0:
        parser.error("--days must be non-negative")
    report = scan(args.home or default_homes(), args.days)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

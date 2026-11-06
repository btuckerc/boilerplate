"""Tool-call fidelity on checkpoints cut from real OMP sessions.

A checkpoint is a session prefix ending just before an assistant turn that called a tool. The model gets
the OMP tool set with tool_choice auto, as in production, and must call a tool whose arguments parse and
carry the schema's required keys; name_match compares the first call with the reference (cloud) model's
choice, which is a reference, not ground truth. A checkpoint whose history calls a tool missing from TOOLS
is dropped: a model copying its own history would be scored invalid, and only on engines that do not
constrain tool names to the offered set (ledger M45).
"""
from __future__ import annotations

import itertools
import json
import random
import statistics
from pathlib import Path

NAME = "toolcall"
VERSION = "4"
METRICS = {"valid": "rate", "name_match": "rate", "called": "rate"}
MUST_PASS = ()  # 50 checkpoints cannot certify a 4-point margin (rule of three); losses still fail
REPORTED = ("name_match",)  # agreement with the cloud model's choice, not correctness
NEEDS_GRADE = False

SESSIONS = Path("/home/tux/.omp/agent/sessions")
SYSTEM = ("You are a coding agent working in a user's repository through tools. Use the tools to inspect "
          "and change files and run commands; call a tool whenever the next step needs one.")


def _fn(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": required}}}


S = {"type": "string"}
TOOLS = [
    _fn("read", "Read a file or directory; line ranges as path suffix, e.g. src/a.py:10-40.",
        {"path": S}, ["path"]),
    _fn("bash", "Run a shell command.", {"command": S, "cwd": S, "timeout": {"type": "number"}}, ["command"]),
    _fn("grep", "Regex search over files.", {"pattern": S, "path": S, "case": {"type": "boolean"}}, ["pattern"]),
    _fn("glob", "List files matching a glob.", {"path": S}, []),
    _fn("find", "Describe behaviour; returns implementing files.",
        {"query": S, "grep_keywords": {"type": "array", "items": S}}, ["query", "grep_keywords"]),
    _fn("edit", "Patch existing files with a hashline patch.", {"input": S}, ["input"]),
    _fn("write", "Create or overwrite a file.", {"path": S, "content": S}, ["path", "content"]),
    _fn("eval", "Run a Python or JS cell.", {"language": {"type": "string", "enum": ["py", "js"]}, "code": S},
        ["language", "code"]),
    _fn("ask", "Ask the user questions with options.", {"questions": {"type": "array", "items": {"type": "object"}}},
        ["questions"]),
    _fn("task", "Spawn subagents for delegated tasks.",
        {"context": S, "tasks": {"type": "array", "items": {"type": "object"}}}, ["context", "tasks"]),
    _fn("wait", "Block until a background job or subagent settles.", {}, []),
    _fn("web_search", "Search the web.", {"query": S}, ["query"]),
]
REQUIRED = {t["function"]["name"]: t["function"]["parameters"]["required"] for t in TOOLS}
MAX_RESULT_CHARS = 4000
MAX_PROMPT_CHARS = 80000  # ~24K tokens


def _text(parts):
    if isinstance(parts, str):
        return parts
    return "\n".join(p.get("text", "") for p in parts or [] if isinstance(p, dict) and p.get("type") == "text")


def _window(history):
    """Most recent messages within MAX_PROMPT_CHARS, starting at a user message so no tool result is orphaned."""
    size, start = 0, len(history)
    for i in range(len(history) - 1, -1, -1):
        size += len(json.dumps(history[i]))
        if size > MAX_PROMPT_CHARS:
            break
        start = i
    while start < len(history) and history[start]["role"] != "user":
        start += 1
    return history[start:]


def extract_checkpoints(lines):
    history, out = [], []
    for line in lines:
        try:
            e = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if e.get("type") == "compaction":
            history = [{"role": "user", "content": "Summary of the session so far:\n" + str(e.get("summary", ""))}]
            continue
        m = e.get("message") if e.get("type") == "message" else None
        if not isinstance(m, dict):
            continue
        role, content = m.get("role"), m.get("content")
        if role == "user":
            text = _text(content)
            if text:
                history.append({"role": "user", "content": text[:MAX_PROMPT_CHARS // 2]})
        elif role == "assistant" and isinstance(content, list):
            calls = [p for p in content if p.get("type") == "toolCall"]
            text = _text(content)
            if calls and calls[0].get("name") in REQUIRED:
                window = _window(history)
                offered = all(c["function"]["name"] in REQUIRED for m in window for c in m.get("tool_calls", ()))
                if window and offered:
                    out.append({"messages": window, "expected_name": calls[0]["name"]})
            msg = {"role": "assistant", "content": text or None}
            if calls:
                msg["tool_calls"] = [{"id": c.get("id", f"call{i}"), "type": "function", "function": {
                    "name": c.get("name", ""), "arguments": json.dumps(c.get("arguments", {}))}} for i, c in enumerate(calls)]
            if text or calls:
                history.append(msg)
        elif role == "toolResult":
            history.append({"role": "tool", "tool_call_id": m.get("toolCallId", ""),
                            "content": _text(content)[:MAX_RESULT_CHARS]})
    return out


def fetch(data_dir):
    files = sorted(SESSIONS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    rng, picked = random.Random(7701), []
    for path in files[:200]:
        with path.open(encoding="utf-8", errors="replace") as f:
            cps = extract_checkpoints(itertools.islice(f, 20000))
        rng.shuffle(cps)
        picked.extend(cps[:5])
        if len(picked) >= 80:
            break
    # Balance tools: at most 12 per reference tool, then 50 in seeded order.
    by = {}
    for cp in picked:
        by.setdefault(cp["expected_name"], []).append(cp)
    chosen = [cp for name in sorted(by) for cp in by[name][:12]]
    rng.shuffle(chosen)
    dest = Path(data_dir) / "toolcall"
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / "checkpoints.jsonl").open("w") as f:
        for i, cp in enumerate(chosen[:50]):
            f.write(json.dumps({"id": f"cp-{i:02d}", **cp}, ensure_ascii=False) + "\n")


def items(tier, opts, data_dir):
    p = Path(data_dir) / "toolcall" / "checkpoints.jsonl"
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    return rows[:10] if tier == "t1" else rows


def score(reply, item):
    calls = reply.tool_calls or []
    name, valid = None, False
    if calls:
        fn = calls[0].get("function", {})
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except (ValueError, TypeError):
            args = None
        name = fn.get("name", "")
        valid = isinstance(args, dict) and name in REQUIRED and set(REQUIRED[name]) <= set(args)
    return {"called": int(bool(calls)), "valid": int(valid), "name_match": int(name == item["expected_name"]),
            "expected": item["expected_name"], "called_name": name, "finish_reason": reply.finish_reason,
            "content_chars": len(reply.content or ""), "reasoning_chars": len(reply.reasoning or "")}


def run_item(ctx, item):
    reply = ctx.chat({"messages": [{"role": "system", "content": SYSTEM}, *item["messages"]], "tools": TOOLS,
                      "tool_choice": "auto", "max_tokens": 8192, "seed": ctx.seed})  # production's n-predict
    return score(reply, item)


def summarize(rows):
    ok = [r for r in rows if "error" not in r]
    out = {"n": len(ok), "errors": len(rows) - len(ok)}
    for k in ("called", "valid", "name_match"):
        out[k] = statistics.mean(r[k] for r in ok) if ok else 0
    return out

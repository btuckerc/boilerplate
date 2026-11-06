"""The HTTP client handed to workloads.

Every request streams, whatever the engine, and every timing a workload sees is
measured here, at the client, from token arrival times and `usage`: the same
boundary for llama.cpp and vLLM. llama.cpp's own server-side `timings` (draft
acceptance and the like) are kept under timings["server"] as diagnostics only.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path("/srv/models/.eval/data")

# Production sampling for Qwen3.8 (thinking, general tasks).
DEFAULT_SAMPLING = {
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "reasoning_effort": "medium",
}


@dataclass
class Reply:
    content: str = ""
    reasoning: str = ""
    tool_calls: list = field(default_factory=list)
    finish_reason: str = ""
    usage: dict = field(default_factory=dict)
    # Client-side: prompt_n (uncached), prompt_ms, prompt_per_second, predicted_n,
    # predicted_ms, predicted_per_second; plus "server": llama.cpp's own timings.
    timings: dict = field(default_factory=dict)
    wall: float = 0.0
    ttft: float | None = None
    raw: dict = field(default_factory=dict)  # the last streamed chunk
    # Ledger M6: the reasoning parser swallowed the answer.
    reasoning_leak: bool = False


class Context:
    def __init__(self, base_url: str, model: str, *, sampling: dict | None = None,
                 request: dict | None = None, seed: int = 0,
                 data_dir: Path = DATA_DIR, run_dir: Path = Path(".")):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.sampling = dict(DEFAULT_SAMPLING if sampling is None else sampling)
        self.request = dict(request or {})  # engine-specific body keys from the candidate
        self.seed = seed
        self.data_dir = Path(data_dir)
        self.run_dir = Path(run_dir)
        self.leaks = 0
        self.replies: list[dict] = []  # what the model said, kept beside its row (ledger M31)

    def chat(self, body: dict, *, timeout: float = 1800) -> Reply:
        payload = {"model": self.model, **self.sampling, **self.request, **body,
                   "stream": True, "stream_options": {"include_usage": True}}
        if payload.get("reasoning_effort"):
            # Engines differ in which of the two reaches the chat template; send
            # both so every engine thinks equally hard.
            payload["chat_template_kwargs"] = {"reasoning_effort": payload["reasoning_effort"],
                                               **payload.get("chat_template_kwargs", {})}
        request = urllib.request.Request(
            self.base_url + "/v1/chat/completions", json.dumps(payload).encode(),
            {"Content-Type": "application/json"})
        start = time.monotonic()
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            detail = error.read()[:500].decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {error.code}: {detail}") from None
        with response:
            reply = _read_stream(response, start)
        self.replies.append({"content": reply.content, "reasoning": reply.reasoning,
                             "tool_calls": reply.tool_calls, "finish_reason": reply.finish_reason,
                             "usage": reply.usage})
        if reply.reasoning_leak:
            self.leaks += 1
        return reply


def _read_stream(lines, start: float) -> Reply:
    content: list[str] = []
    reasoning: list[str] = []
    calls: dict[int, dict] = {}
    finish_reason = ""
    usage: dict = {}
    timings: dict = {}
    last: dict = {}
    first = last_token = None
    for line in lines:
        line = line.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        chunk = json.loads(data)
        if "error" in chunk:
            raise RuntimeError(f"stream error: {json.dumps(chunk['error'])[:500]}")
        last = chunk
        usage = chunk.get("usage") or usage
        timings = chunk.get("timings") or timings
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            text = delta.get("content") or ""
            thought = delta.get("reasoning_content") or delta.get("reasoning") or ""
            if text or thought or delta.get("tool_calls"):
                last_token = time.monotonic()
                first = first or last_token
            content.append(text)
            reasoning.append(thought)
            for call in delta.get("tool_calls") or []:
                _merge_tool_call(calls, call)
            finish_reason = choice.get("finish_reason") or finish_reason
    end = time.monotonic()
    text, thought = "".join(content), "".join(reasoning)
    ttft = None if first is None else first - start
    timings = {**_client_timings(usage, ttft, first, last_token), "server": timings}
    return Reply(
        content=text, reasoning=thought,
        tool_calls=[calls[i] for i in sorted(calls)],
        finish_reason=finish_reason, usage=usage, timings=timings,
        wall=end - start, ttft=ttft, raw=last,
        reasoning_leak=finish_reason == "stop" and not text.strip() and bool(thought.strip()))


def _merge_tool_call(calls: dict[int, dict], delta: dict) -> None:
    """OpenAI streams a tool call as fragments keyed by `index`."""
    call = calls.setdefault(delta.get("index", len(calls)),
                            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
    call["id"] = delta.get("id") or call["id"]
    function = delta.get("function") or {}
    call["function"]["name"] += function.get("name") or ""
    call["function"]["arguments"] += function.get("arguments") or ""


def _client_timings(usage: dict, ttft, first, last_token) -> dict:
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    prompt_n = max(0, (usage.get("prompt_tokens") or 0) - cached)
    predicted_n = usage.get("completion_tokens") or 0
    decode_s = (last_token - first) if first is not None else 0.0
    return {
        "prompt_n": prompt_n,
        "prompt_ms": (ttft or 0.0) * 1000,
        "prompt_per_second": prompt_n / ttft if ttft else 0.0,
        "predicted_n": predicted_n,
        "predicted_ms": decode_s * 1000,
        # The first token arrives with the prefill; decode speed covers the rest.
        "predicted_per_second": (predicted_n - 1) / decode_s if decode_s > 0 and predicted_n > 1 else 0.0,
    }

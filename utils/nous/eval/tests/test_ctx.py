import io
import json
import urllib.error

import pytest

from nevl import ctx
from nevl.ctx import Context


def sse(*chunks):
    lines = [f"data: {json.dumps(c)}\n".encode() for c in chunks] + [b"data: [DONE]\n"]

    class Response(io.BytesIO):
        def __iter__(self):
            return iter(lines)

    return Response()


def serve(monkeypatch, *chunks):
    sent = {}

    def urlopen(request, timeout):
        sent["body"] = json.loads(request.data)
        return sse(*chunks)

    monkeypatch.setattr(ctx.urllib.request, "urlopen", urlopen)
    return sent


def delta(**fields):
    return {"choices": [{"delta": fields, "finish_reason": None}]}


def test_tool_call_fragments_are_assembled_by_index(monkeypatch):
    serve(monkeypatch,
          delta(tool_calls=[{"index": 0, "id": "c1", "function": {"name": "read", "arguments": '{"pa'}}]),
          delta(tool_calls=[{"index": 1, "id": "c2", "function": {"name": "grep", "arguments": "{}"}}]),
          delta(tool_calls=[{"index": 0, "function": {"arguments": 'th": "a.py"}'}}]),
          {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]})
    reply = Context("http://x", "m").chat({"messages": []})
    assert [c["function"]["name"] for c in reply.tool_calls] == ["read", "grep"]
    assert json.loads(reply.tool_calls[0]["function"]["arguments"]) == {"path": "a.py"}
    assert reply.finish_reason == "tool_calls"


def test_timings_are_measured_at_the_client_on_every_engine(monkeypatch):
    """One boundary for llama.cpp and vLLM (council A-02/O-07): server timings never
    replace client ones; prefill excludes prefix-cached tokens."""
    usage = {"prompt_tokens": 1000, "completion_tokens": 3, "prompt_tokens_details": {"cached_tokens": 600}}
    for server in ({}, {"predicted_per_second": 999.0, "prompt_n": 12}):
        serve(monkeypatch, delta(content="a"), delta(content="b"), delta(content="c"),
              {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": usage, "timings": server})
        reply = Context("http://x", "m").chat({"messages": []})
        assert reply.timings["prompt_n"] == 400 and reply.timings["predicted_n"] == 3
        assert reply.timings["predicted_per_second"] != 999.0
        assert reply.timings["server"] == server
        assert reply.content == "abc" and reply.ttft is not None


def test_reasoning_leak_flagged_and_counted(monkeypatch):
    serve(monkeypatch, delta(reasoning_content="thinking only"),
          {"choices": [{"delta": {}, "finish_reason": "stop"}]})
    context = Context("http://x", "m")
    assert context.chat({"messages": []}).reasoning_leak
    assert context.leaks == 1


def test_truncated_reasoning_is_not_a_leak(monkeypatch):
    serve(monkeypatch, delta(reasoning_content="long thought"),
          {"choices": [{"delta": {}, "finish_reason": "length"}]})
    assert not Context("http://x", "m").chat({"messages": []}).reasoning_leak


def test_body_overrides_sampling_and_request_keys(monkeypatch):
    sent = serve(monkeypatch, {"choices": [{"delta": {"content": "x"}, "finish_reason": "stop"}]})
    Context("http://x", "m", request={"chat_template_kwargs": {"a": 1}}).chat(
        {"messages": [], "temperature": 0.0})
    body = sent["body"]
    assert body["temperature"] == 0.0 and body["top_k"] == 20
    assert body["chat_template_kwargs"] == {"reasoning_effort": "medium", "a": 1}
    assert body["stream"] is True and body["model"] == "m"


def test_http_error_carries_the_server_message(monkeypatch):
    def urlopen(request, timeout):
        raise urllib.error.HTTPError("http://x", 400, "bad", {}, io.BytesIO(b"context too long"))

    monkeypatch.setattr(ctx.urllib.request, "urlopen", urlopen)
    with pytest.raises(RuntimeError, match="HTTP 400: context too long"):
        Context("http://x", "m").chat({"messages": []})


def test_reasoning_effort_reaches_the_template_on_every_engine(monkeypatch):
    sent = serve(monkeypatch, {"choices": [{"delta": {"content": "x"}, "finish_reason": "stop"}]})
    Context("http://x", "m").chat({"messages": [], "reasoning_effort": "low"})
    assert sent["body"]["reasoning_effort"] == "low"
    assert sent["body"]["chat_template_kwargs"] == {"reasoning_effort": "low"}

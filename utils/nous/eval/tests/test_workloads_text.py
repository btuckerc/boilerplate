import io
import json
import urllib.error
from types import SimpleNamespace

import pytest

from nevl.workloads import concurrency, longctx
from nevl.workloads.toolcall import extract_checkpoints, score


def test_needles_are_all_planted_in_order_and_spread_out():
    needles = {f"key_{i}": f"value_{i}" for i in range(8)}
    lines = longctx._plant("".join(f"filler {n}\n" for n in range(80)), needles).splitlines()
    where = [n for n, line in enumerate(lines) if line.startswith("Record ")]
    assert [lines[n] for n in where] == [f"Record {i}: lookup key_{i} has value value_{i}." for i in range(8)]
    assert len(lines) == 88 and 0 < where[0] and where[-1] < len(lines) - 1
    assert all(8 <= b - a <= 12 for a, b in zip(where, where[1:]))


def _fake_tokenize(monkeypatch, accepts):
    """/tokenize as observed: the llama.cpp router ('content') needs `model` and answers
    a `prompt` body with no tokens; vLLM ('prompt') rejects a body without `prompt`."""
    def urlopen(request, timeout):
        body = json.loads(request.data)
        if "model" not in body or (accepts == "prompt" and "prompt" not in body):
            raise urllib.error.HTTPError(request.full_url, 400, "bad", {}, io.BytesIO(b""))
        n = len(body.get(accepts, "")) // 4
        reply = {"tokens": list(range(n))} if accepts == "content" else {"count": n, "tokens": list(range(n))}
        return io.BytesIO(json.dumps(reply).encode())
    monkeypatch.setattr(longctx.urllib.request, "urlopen", urlopen)


@pytest.mark.parametrize("engine", ["content", "prompt"])
def test_token_counts_work_on_llama_and_vllm(monkeypatch, engine):
    _fake_tokenize(monkeypatch, engine)
    ctx = SimpleNamespace(base_url="http://x", model="m")
    assert longctx._count_tokens(ctx, "a" * 400) == 100
    fitted = longctx._fit(ctx, "a" * 400000, 50000)
    assert 50000 * 4 - 2000 <= len(fitted) <= 50000 * 4


def test_longctx_prompts_never_share_a_cacheable_prefix(monkeypatch, tmp_path):
    """A shared prefix would let a prefix-caching engine skip the prefill being measured."""
    _fake_tokenize(monkeypatch, "content")
    (tmp_path / "longctx").mkdir()
    (tmp_path / "longctx" / "filler.txt").write_text("".join(f"line {n}\n" for n in range(40000)))
    prompts = []

    def chat(body):
        prompts.append(body["messages"][0]["content"])
        return SimpleNamespace(content="{}", timings={}, wall=1.0, finish_reason="stop")

    for seed in (1000, 2000):
        for depth in (2000, 4000):
            ctx = SimpleNamespace(base_url="http://x", model="m", seed=seed, data_dir=tmp_path, chat=chat)
            longctx.run_item(ctx, {"id": f"depth-{depth}", "depth": depth})
    first_lines = {prompt.splitlines()[0] for prompt in prompts}
    assert len(first_lines) == len(prompts) == 4

def test_checkpoint_extraction_keeps_tool_structure_and_reference():
    events = [
        {'type':'message','message':{'role':'user','content':[{'type':'text','text':'Please inspect this file'}]}},
        {'type':'message','message':{'role':'assistant','content':[{'type':'thinking','thinking':'x'},{'type':'toolCall','id':'c1','name':'read','arguments':{'path':'src/a.py'}}]}},
        {'type':'message','message':{'role':'toolResult','toolCallId':'c1','toolName':'read','content':[{'type':'text','text':'def f(): pass'}]}},
        {'type':'message','message':{'role':'assistant','content':[{'type':'toolCall','id':'c2','name':'edit','arguments':{'input':'...'}}]}},
        {'type':'message','message':{'role':'assistant','content':[{'type':'toolCall','id':'c3','name':'lsp','arguments':{}}]}},
    ]
    cps = extract_checkpoints([json.dumps(e) for e in events])
    assert [c['expected_name'] for c in cps] == ['read', 'edit']  # 'lsp' is not in the offered tool set
    second = cps[1]['messages']
    assert second[0] == {'role':'user','content':'Please inspect this file'}
    assert second[1]['tool_calls'][0]['function'] == {'name':'read','arguments':'{"path": "src/a.py"}'}
    assert second[2] == {'role':'tool','tool_call_id':'c1','content':'def f(): pass'}

def test_checkpoint_after_compaction_starts_from_summary():
    events = [
        {'type':'message','message':{'role':'user','content':[{'type':'text','text':'old'}]}},
        {'type':'compaction','summary':'did things'},
        {'type':'message','message':{'role':'assistant','content':[{'type':'toolCall','id':'c','name':'bash','arguments':{'command':'ls'}}]}},
    ]
    cps = extract_checkpoints([json.dumps(e) for e in events])
    assert cps[0]['messages'] == [{'role':'user','content':'Summary of the session so far:\ndid things'}]

def test_a_checkpoint_whose_history_calls_an_unoffered_tool_is_dropped():
    """The model would be scored invalid for copying its own history, and only on engines without name grammar (M45)."""
    events = [
        {'type':'message','message':{'role':'user','content':[{'type':'text','text':'check types'}]}},
        {'type':'message','message':{'role':'assistant','content':[{'type':'toolCall','id':'c1','name':'lsp','arguments':{}}]}},
        {'type':'message','message':{'role':'toolResult','toolCallId':'c1','toolName':'lsp','content':[{'type':'text','text':'ok'}]}},
        {'type':'message','message':{'role':'assistant','content':[{'type':'toolCall','id':'c2','name':'bash','arguments':{'command':'make'}}]}},
        {'type':'compaction','summary':'started the build'},
        {'type':'message','message':{'role':'assistant','content':[{'type':'toolCall','id':'c3','name':'wait','arguments':{}}]}},
    ]
    cps = extract_checkpoints([json.dumps(e) for e in events])
    assert [c['expected_name'] for c in cps] == ['wait']
    assert cps[0]['messages'] == [{'role':'user','content':'Summary of the session so far:\nstarted the build'}]

def _reply(calls):
    return SimpleNamespace(tool_calls=calls, finish_reason='tool_calls', content='', reasoning='')

def test_toolcall_validity_requires_json_and_the_called_tools_required_keys():
    item = {'expected_name':'read'}
    fn = lambda name, args: [{'function':{'name':name,'arguments':args}}]
    assert score(_reply(fn('read','{"path":"x"}')), item)['valid'] == 1
    assert score(_reply(fn('read','{}')), item)['valid'] == 0
    assert score(_reply(fn('grep','not json')), item)['valid'] == 0
    other = score(_reply(fn('grep','{"pattern":"a"}')), item)
    assert other['valid'] == 1 and other['name_match'] == 0
    assert score(_reply([]), item)['called'] == 0

def test_needle_answer_parsing_accepts_fenced_and_trailing_json():
    assert longctx._last_json_object('Here:\n```json\n{"key_0": "value_1"}\n```') == {'key_0': 'value_1'}
    assert longctx._last_json_object('noise {bad} then {"key_1": "value_2"}') == {'key_1': 'value_2'}
    assert longctx._last_json_object('no json') == {}


def test_a_request_failing_under_load_fails_the_item():
    """A failed request is an engine failure, never a fast, partly-scored item (council A-08)."""
    def chat(body):
        if "agent 1;" in body["messages"][0]["content"] and len(body["messages"]) == 5:
            raise RuntimeError("HTTP 500: slot unavailable")
        return SimpleNamespace(content="ok", timings={"prompt_n": 10}, wall=0.1, ttft=0.05)

    ctx = SimpleNamespace(seed=0, chat=chat)
    with pytest.raises(RuntimeError, match="1 of 5 requests failed with 2 clients: HTTP 500"):
        concurrency.run_item(ctx, {"clients": 2, "sessions": 2, "doc_tokens": 100})

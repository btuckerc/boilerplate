import pytest

from nevl.sandbox import run_python
from nevl.workloads import vision


def test_sandbox_python_and_limits():
    rc, out, err, timed = run_python("print(6*7)", "", 5)
    assert (rc, out.strip(), timed) == (0, "42", False)
    rc, _, _, timed = run_python("while True: pass", "", 1)
    assert timed or rc != 0
    rc, _, _, timed = run_python("a=bytearray(3*1024**3)", "", 5, 128)
    assert rc != 0 and not timed


def test_sandbox_blocks_network_home_and_home_read():
    src = """import socket\ns=socket.socket()\ntry: s.connect(('1.1.1.1',80)); print('connected')\nexcept OSError: print('blocked')"""
    rc, out, _, _ = run_python(src, "", 5)
    assert rc == 0 and "blocked" in out
    rc, out, _, _ = run_python("open('/home/escape','w').write('x')", "", 5)
    assert rc != 0
    rc, out, _, _ = run_python("open('/home/tux/.profile').read()", "", 5)
    assert rc != 0


class Reply:
    reasoning = ""
    tool_calls = []
    finish_reason = "stop"
    usage = {"prompt_tokens": 12}
    timings = {}
    wall = 0.1
    ttft = 0.01
    raw = {}


class FakeContext:
    seed = 0

    def __init__(self, content=""):
        self.content = content

    def chat(self, body, **kwargs):
        self.body = body
        self.reply = Reply()
        self.reply.content = self.content
        return self.reply


def test_vision_items_seed_and_request_construction(tmp_path):
    a = vision.items("t1", {"seed": 8}, tmp_path)
    b = vision.items("t1", {"seed": 8}, tmp_path)
    assert len(a) == 3
    assert [x["need"] for x in a] == [x["need"] for x in b]
    ctx = FakeContext(" ".join(a[0]["need"]))
    row = vision.run_item(ctx, a[0])
    assert row["pass"]
    parts = ctx.body["messages"][0]["content"]
    assert any(x["type"] == "image_url" and x["image_url"]["url"].startswith("data:image/png;base64,") for x in parts)





#!/usr/bin/env python3
"""Minimal local OpenAI-compatible capture endpoint for the evaluator."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    out = None

    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            self._send({"object": "list", "data": [{"id": "capture", "object": "model", "owned_by": "omp-context-eval"}]})
        else:
            self.send_error(404)

    def do_POST(self):
        size = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(size)
        if self.path.endswith("/chat/completions"):
            payload = json.loads(body)
            with self.out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
            if payload.get("stream"):
                chunks = [
                    {"id": "capture", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "CAPTURE_COMPLETE"}, "finish_reason": None}]},
                    {"id": "capture", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
                ]
                raw = b"".join((b"data: " + json.dumps(c).encode() + b"\n\n" for c in chunks)) + b"data: [DONE]\n\n"
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("content-length", str(len(raw)))
                self.end_headers(); self.wfile.write(raw)
            else:
                self._send({"id": "capture", "object": "chat.completion", "choices": [{"index": 0, "message": {"role": "assistant", "content": "CAPTURE_COMPLETE"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1}})
        else:
            self.send_error(404)

    def _send(self, obj):
        raw = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    Handler.out = args.out
    HTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

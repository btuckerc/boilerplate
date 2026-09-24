#!/usr/bin/env python3
"""Capture real OMP 18.2.6 provider requests against a local mock endpoint."""
from __future__ import annotations
import argparse, base64, json, pathlib, subprocess, tempfile, time
from datetime import datetime, timezone
from typing import Any

SERVER = pathlib.Path(__file__).with_name("capture_server.py")

def _remote_counts(texts: list[str], host: str) -> tuple[list[int] | None, str]:
    body = json.dumps({"texts": texts}, ensure_ascii=False).encode()
    script = ("import json,sys,urllib.request;d=json.load(sys.stdin);m=json.load(urllib.request.urlopen('http://127.0.0.1:8080/v1/models',timeout=3));l=next((x for x in m.get('data',[]) if x.get('status',{}).get('value')=='loaded'),None);a=(l or {}).get('status',{}).get('args',[]);p=a[a.index('--port')+1] if '--port' in a else '60053';o=[]\nfor t in d['texts']:\n r=urllib.request.Request('http://127.0.0.1:'+p+'/tokenize',data=json.dumps({'content':t}).encode(),headers={'content-type':'application/json'});o.append(len(json.load(urllib.request.urlopen(r,timeout=10))['tokens']))\nprint(json.dumps({'model':(l or {}).get('id','unknown'),'port':p,'counts':o}))")
    enc = base64.b64encode(script.encode()).decode(); cmd = f'''python3 -c "import base64;exec(base64.b64decode('{enc}'))"'''
    try:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, cmd], input=body, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
        d = json.loads(p.stdout); return d["counts"], f"remote-exact:{d['model']}:{d['port']}"
    except Exception as exc: return None, f"remote-unavailable:{type(exc).__name__}"

def _estimate(text: str) -> int: return (len(text.encode("utf-8")) + 3) // 4

PROFILES = {
    "isolated-xdev-catalog-no-discovery": {"xdev": True, "tools": None, "label": "isolated xdev=true/catalog; discovery disabled"},
    "isolated-xdev-disabled-no-discovery": {"xdev": False, "tools": None, "label": "isolated xdev=false; discovery disabled"},
    "baseline-six-file-tools": {"xdev": True, "tools": "read,grep,glob,edit,write,yield", "label": "current six-tool standalone baseline; not a spawned task child"},
    "candidate-three-tools-approximation": {"xdev": True, "tools": "read,write,yield", "label": "unpromoted three-tool candidate; not a spawned task child"},
    "scoped-read-edit-write-bash": {"xdev": False, "tools": "read,edit,write,bash", "label": "standalone scoped tool restriction"},
}

def _files(root: pathlib.Path, xdev: bool) -> None:
    (root / "models.yml").write_text("""providers:\n  loopback:\n    baseUrl: http://127.0.0.1:18765/v1\n    api: openai-completions\n    auth: none\n    models:\n      - id: capture\n        name: Capture\n        contextWindow: 32768\n        maxTokens: 64\n""", encoding="utf-8")
    (root / "config.yml").write_text(f"""disabledProviders: [openai-codex, anthropic, openrouter, google, github-copilot]\ntools:\n  xdev: {str(xdev).lower()}\n  approvalMode: yolo\nskills:\n  enablePiUser: false\n  enablePiProject: false\n  enableCodexUser: false\n  enableCodexProject: false\n  enableClaudeUser: false\n  enableClaudeProject: false\n  enableAgentsUser: false\n  enableAgentsProject: false\nstartup:\n  quiet: true\n  showSplash: false\n""", encoding="utf-8")

def _capture(profile: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = PROFILES[profile]
    with tempfile.TemporaryDirectory(prefix="omp-context-native-") as td:
        base = pathlib.Path(td); agent = base / "agent"; cwd = base / "cwd"; agent.mkdir(); cwd.mkdir(); _files(agent, spec["xdev"]); capture = base / "requests.jsonl"
        server = subprocess.Popen(["python3", str(SERVER), "--port", "18765", "--out", str(capture)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.15); cmd = ["omp", "--model", "loopback/capture", "--cwd", str(cwd), "-p", "--no-session", "--no-skills", "--no-rules", "--no-extensions", "--no-lsp", "--thinking", "off", "--max-time", "8", "--auto-approve"]
            if spec["tools"]: cmd += ["--tools", spec["tools"]]
            cmd += ["Synthetic capture task: return CAPTURE_COMPLETE and do not call tools."]
            env = {"PATH": "/Users/tucker/.local/share/mise/installs/github-can1357-oh-my-pi/18.2.6:/usr/bin:/bin:/usr/local/bin", "PI_CODING_AGENT_DIR": str(agent), "HOME": str(base), "TMPDIR": str(base)}
            run = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            error = None if run.returncode == 0 else f"omp_exit:{run.returncode}:{run.stderr.decode(errors='replace')[-400:]}"
        except Exception as exc:
            run = None; error = f"subprocess:{type(exc).__name__}:{exc}"
        finally:
            server.terminate(); server.wait(timeout=3)
        requests = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines()] if capture.exists() else []
        return requests, {"return_error": error, "stdout": (run.stdout.decode(errors="replace")[-200:] if run else "")}

def _components(request: dict[str, Any]) -> tuple[str, str, str]:
    system = "\n".join(str(m.get("content", "")) for m in request.get("messages", []) if m.get("role") == "system")
    tools = json.dumps(request.get("tools", []), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    wire = json.dumps(request, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return system, tools, wire

def measure(tokenizer: str = "auto", host: str = "nous") -> dict[str, Any]:
    rows = []
    for name, spec in PROFILES.items():
        requests, status = _capture(name)
        if not requests:
            rows.append({"profile": name, "description": spec["label"], "capture": "blocked", "error": status["return_error"] or "no provider request"}); continue
        request = requests[0]; system, tools, wire = _components(request); texts = [system, tools, wire]; counts = None; source = "estimate:bytes/4"
        if tokenizer in ("auto", "remote"): counts, source = _remote_counts(texts, host)
        if counts is None and tokenizer == "remote": raise RuntimeError(f"exact tokenizer required but unavailable ({source})")
        if counts is None: counts = [_estimate(t) for t in texts]
        rows.append({"profile": name, "description": spec["label"], "capture": "native-openai-completions", "request_count": len(requests), "model": request.get("model"), "message_count": len(request.get("messages", [])), "tool_count": len(request.get("tools", [])), "stream": request.get("stream"), "system_bytes": len(system.encode()), "tool_schema_bytes": len(tools.encode()), "wire_bytes": len(wire.encode()), "system_tokens": counts[0], "tool_schema_tokens": counts[1], "wire_tokens": counts[2], "token_count_source": source, "status": status})
    return {"schema": 2, "generated_at": datetime.now(timezone.utc).isoformat(), "omp_version": "18.2.6", "fixture": "native-subprocess-loopback", "rows": rows, "limitations": ["Loopback response is synthetic; no inference occurs.", "The captured request is the actual native provider serialization for this isolated fixture.", "Provider-specific hidden gateway framing is absent; wire count is the exact captured JSON body."]}

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--out", type=pathlib.Path, required=True); ap.add_argument("--tokenizer", choices=("auto", "remote", "estimate"), default="auto"); ap.add_argument("--host", default="nous"); args = ap.parse_args(argv)
    result = measure(args.tokenizer, args.host); args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8"); print(json.dumps(result, indent=2)); return 0

if __name__ == "__main__": raise SystemExit(main())

import json, os, resource, time
from pathlib import Path
import torch
from huggingface_hub import snapshot_download
import laya

os.environ["CUDA_VISIBLE_DEVICES"] = ""
torch.set_num_threads(4)
torch.set_num_interop_threads(1)
REV = "c5d78730f3493e4fe16d61507ef4b78eef7318cf"
ROOT = Path("/home/tux/.local/share/nous-triage-eval")
model_path = snapshot_download("convaiinnovations/laya", revision=REV, local_dir=ROOT / "base-model", local_dir_use_symlinks=False, allow_patterns=["encoder/*", "model.safetensors", "rl_agent_config.json", "tokenizer/*", "*.json"])
load_start = time.perf_counter()
agent = laya.load(model_path, device="cpu")
agent.cfg["head_max_len"] = 256
cold_ms = (time.perf_counter() - load_start) * 1000

criteria = {
    "local": "Bounded mechanical file transform or extraction using supplied text, one file, cheap exact verification. Local 9B model is weak at algorithmic reasoning, tools and large context; never use it for diagnosing unknown bugs or independent arithmetic design.",
    "luna": "Capable coding model for ordinary implementation, tests, navigation, routine computer use and bounded debugging. Default for clear implementable work. Can use tools and run tests.",
    "astra": "Frontier reasoning for ambiguous architecture, unexplained repeated failures, deep conflicting research or hard decisions. Higher cost; unnecessary for routine edits.",
    "retain": "Context-dependent continuation or unclear request that cannot be safely classified from the provided text. Preserve the current model; do not guess.",
}
cases = [
 ("extract", "Read the supplied 30-row CSV and return the five rows with status failed. No web access or inference required.", "local"),
 ("format", "Convert palette.json to palette.csv preserving exact row order and numeric values. Only output format changes.", "local"),
 ("overflow", "Fix the indexed4 row byte calculation for odd widths and SIZE_MAX without integer overflow, then compile and run the existing tests.", "luna"),
 ("rename", "Rename a TypeScript function across 12 files, update imports and run the test suite.", "luna"),
 ("ui", "Change the CSS button padding from 8px to 12px and verify the page.", "luna"),
 ("architecture", "Design the asynchronous DMA buffer ownership and cancellation protocol for an ESP32 renderer sharing PSRAM with an emulator. Timing is inconsistent and the cause is unknown.", "astra"),
 ("diagnosis", "Three attempted fixes still produce rare corrupted video frames; logs contradict the presumed ownership model. Diagnose root cause across interrupts and DMA callbacks.", "astra"),
 ("research", "Critically compare agent execution policies using primary research and reconcile conflicting evidence before choosing the architecture.", "astra"),
 ("continue", "Continue.", "retain"),
 ("steer", "Actually use Luna for this task.", "luna"),
 ("override", "Keep this entirely local. Summarize the supplied 1KB build log.", "local"),
 ("ambiguous", "Make it better.", "retain"),
]
questions = {"route": {"type": "choice", "instructions": "Choose the cheapest suitable execution tier for this request based only on supplied evidence. Honor an explicit model or local-only request. Do not assume missing conversation or code context. This is task triage, not permission or proof the task will succeed.", "criteria": criteria}}
results = []
for name, prompt, expected in cases:
    started = time.perf_counter()
    try:
        answer = agent.predict({"request": prompt}, questions).get("answers", {}).get("route", {})
        error = None
    except Exception as exc:
        answer = {}
        error = type(exc).__name__ + ": " + str(exc)[:200]
    results.append({"case": name, "expected": expected, "answer": answer, "ms": round((time.perf_counter() - started) * 1000, 2), "error": error})
print(json.dumps({"model": "convaiinnovations/laya", "revision": REV, "head_max_len": 256, "cold_load_ms": round(cold_ms, 2), "rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "threads": 4, "results": results}, indent=2))

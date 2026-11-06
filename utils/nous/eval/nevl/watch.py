"""Track upstream model and inference-engine changes without running GPU work."""
from __future__ import annotations

import json
import os
import sys
import time
import tomllib
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import store
from .build import RADIANCE_REPO, latest_radiance_release
from .candidate import incumbent

TIMEOUT = 30
USER_AGENT = "nous-eval"
REPO_ROOT = Path(__file__).resolve().parents[3].parent
CONFIG = Path(__file__).resolve().parents[1] / "watch.toml"
ARTIFACTS = REPO_ROOT / "utils/nous/model-artifacts.json"
STALL_S = 6 * 3600  # no row for this long and no done.json: the run is not running (power loss, killed unit)


def stalled_runs(runs: Path, now: float) -> list[dict]:
    """Started runs (rows.jsonl exists) that never finished and have written nothing for STALL_S."""
    stalled = []
    for rows in sorted(runs.glob("*/rows.jsonl")):
        if not (rows.parent / "done.json").exists() and now - rows.stat().st_mtime > STALL_S:
            stalled.append({"run_id": rows.parent.name, "last_row": rows.stat().st_mtime})
    return stalled


def _get(url: str, accept: str = "application/json"):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


def fetch_hf_model(repo: str):
    return _get(f"https://huggingface.co/api/models/{repo}")


def fetch_hf_author(author: str):
    query = urllib.parse.urlencode({"author": author, "sort": "createdAt", "direction": "-1", "limit": 50})
    return _get(f"https://huggingface.co/api/models?{query}")


def fetch_github(repo: str):
    return _get(f"https://api.github.com/repos/{repo}/releases/latest", "application/vnd.github+json")


def fetch_docker(repo: str):
    return _get(f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=10")


def production_repositories(production: dict, artifacts: dict) -> list[dict]:
    spec = production["spec"]
    mounts = spec.get("mounts", {})
    directories = []
    for arg in spec.get("args", []):
        if not isinstance(arg, str):
            continue
        for inside, host in mounts.items():
            if arg == inside or arg.startswith(inside.rstrip("/") + "/"):
                directories.append((inside, host, arg))
    result = {}
    for entry in artifacts["models"]:
        file = entry.get("file", "")
        for inside, host, arg in directories:
            host_dir = Path(host) / Path(arg).relative_to(inside)
            try:
                Path(file).relative_to(host_dir)
            except ValueError:
                continue
            result[entry["repository"]] = entry
            break
    return [{"repo": repo, "recorded_revision": entry.get("revision"), "upstream_sha": None}
            for repo, entry in result.items()]


def findings(config: dict, snapshot: dict, seen: dict | None) -> tuple[list[dict], dict]:
    fresh = seen is None
    state = json.loads(json.dumps(seen or {"hf": {}, "github": {}, "docker": {}}))
    items = []
    for row in snapshot.get("production", []):
        if row.get("upstream_sha") and row["upstream_sha"] != row.get("recorded_revision"):
            items.append({"kind": "open", "source": row["repo"], "url": f"https://huggingface.co/{row['repo']}",
                          "text": f"{row['repo']} upstream revision {row['upstream_sha']} differs from recorded {row.get('recorded_revision')}; update model-artifacts.json and review promotion."})
    if fresh:
        counts = []
        for author, models in snapshot.get("authors", {}).items():
            state["hf"][author] = sorted({m["id"] if isinstance(m, dict) else m for m in models})
            counts.append(f"{author}: {len(models)} models")
        for repo, release in snapshot.get("github", {}).items():
            state["github"][repo] = release.get("tag")
            counts.append(f"{repo}: {release.get('tag', 'unavailable')}")
        for repo, tag in snapshot.get("docker", {}).items():
            state["docker"][repo] = tag
            counts.append(f"{repo}: {tag or 'unavailable'}")
        items.append({"kind": "baseline", "source": "baseline", "text": "Baseline seeded: " + "; ".join(counts)})
    else:
        why = {entry.get("author") or entry.get("repo"): entry.get("why", "")
               for kind in ("hf_author", "github_release", "docker_tag") for entry in config.get(kind, [])}
        for author, models in snapshot.get("authors", {}).items():
            ids = {m["id"] if isinstance(m, dict) else m for m in models}
            known = set(state["hf"].get(author, []))
            for model in sorted(ids - known):
                items.append({"kind": "new", "source": author, "url": f"https://huggingface.co/{model}",
                              "text": f"New Hugging Face model: {model} ({why.get(author, author)})"})
            state["hf"][author] = sorted(known | ids)
        for repo, release in snapshot.get("github", {}).items():
            tag = release.get("tag")
            if tag and state["github"].get(repo) != tag:
                items.append({"kind": "new", "source": repo, "url": release.get("url"),
                              "text": f"New release: {repo} {tag} ({why.get(repo, repo)})"})
            if tag:
                state["github"][repo] = tag
        for repo, tag in snapshot.get("docker", {}).items():
            if tag and state["docker"].get(repo) != tag:
                items.append({"kind": "new", "source": repo, "url": f"https://hub.docker.com/r/{repo}/tags",
                              "text": f"New Docker tag: {repo}:{tag} ({why.get(repo, repo)})"})
            if tag:
                state["docker"][repo] = tag
    release = snapshot.get("github", {}).get(RADIANCE_REPO)
    if release and release.get("tag"):
        production_running = snapshot.get("production_radiance", False)
        release_key = release["tag"].removeprefix("v")
        record = snapshot.get("canary", {}).get(release_key)
        if record:
            items.append({"kind": "status", "source": RADIANCE_REPO,
                          "text": f"Canary {release['tag']}: verdict {record.get('verdict')}; run {record.get('run_id')}; t3 run {record.get('t3_run_id')}.", "url": release.get("url")})
        elif not production_running:
            items.append({"kind": "status", "source": RADIANCE_REPO,
                          "text": f"Canary {release['tag']} did not finish; inspect `journalctl --user -u nous-eval-canary`.", "url": release.get("url")})
    for error in snapshot.get("errors", []):
        items.append({"kind": "error", "source": error["source"],
                      "text": f"Could not check {error['source']}: {error['error']}"})
    for run in snapshot.get("stalled", []):
        last = datetime.fromtimestamp(run["last_row"], timezone.utc).isoformat(timespec="minutes")
        items.append({"kind": "open", "source": run["run_id"],
                      "text": f"Run {run['run_id']} stopped without finishing (last row {last}); "
                              f"`./nous-eval resume {run['run_id']}` in a user unit."})
    return items, state


def _atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _render(items: list[dict]) -> str:
    lines = ["# nous inference upstream watch", ""]
    if not items:
        return "\n".join(lines + ["Nothing new or open.", ""])
    lines += [f"- {item['text']}" + (f" ([link]({item['url']}))" if item.get("url") else "") for item in items]
    lines += ["", "Next steps: a new model or engine is measured with `./nous-eval run t2 --incumbent -c "
              "candidates/CANDIDATE.toml`, then t3, then `./nous-eval promote LABEL --run T2_RUN --run T3_RUN`; "
              "a changed production revision is reviewed and recorded in `utils/nous/model-artifacts.json`.", ""]
    return "\n".join(lines)


def run() -> int:
    try:
        config = tomllib.loads(CONFIG.read_text())
        artifacts = json.loads(ARTIFACTS.read_text())
        production = incumbent()
        watch_dir = store.root() / "watch"
        seen_path = watch_dir / "seen.json"
        seen = json.loads(seen_path.read_text()) if seen_path.exists() else None
        snapshot = {"production": production_repositories(production, artifacts), "authors": {}, "github": {},
                    "docker": {}, "canary": {}, "stalled": stalled_runs(store.root() / "runs", time.time())}

        for row in snapshot["production"]:
            try:
                row["upstream_sha"] = fetch_hf_model(row["repo"]).get("sha")
            except Exception as exc:
                snapshot.setdefault("errors", []).append({"source": row["repo"], "error": str(exc)})
        for source, entries in (("hf_author", config.get("hf_author", [])), ("github_release", config.get("github_release", [])), ("docker_tag", config.get("docker_tag", []))):
            for entry in entries:
                repo = entry["author"] if source == "hf_author" else entry["repo"]
                try:
                    if source == "hf_author":
                        snapshot["authors"][repo] = fetch_hf_author(repo)
                    elif source == "github_release":
                        payload = fetch_github(repo)
                        release = {"tag": payload["tag_name"], "url": payload.get("html_url"),
                                   "published_at": payload.get("published_at")}
                        if repo == RADIANCE_REPO:
                            release["image_tag"] = latest_radiance_release(payload)["image_tag"]
                        snapshot["github"][repo] = release
                    else:
                        tags = fetch_docker(repo).get("results", [])
                        snapshot["docker"][repo] = next((tag["name"] for tag in tags if tag.get("name") != "latest"), None)
                except Exception as exc:
                    snapshot.setdefault("errors", []).append({"source": repo, "error": str(exc)})
        release = snapshot["github"].get(RADIANCE_REPO, {})
        rootfs = production.get("spec", {}).get("rootfs", "")
        snapshot["production_radiance"] = bool(release.get("image_tag") and rootfs.endswith(
            f"vllm-sly-radiance-{release['image_tag']}"))
        if release.get("tag"):
            path = store.root() / "canary" / f"radiance-{release['tag'].removeprefix('v')}.json"
            if path.exists():
                snapshot["canary"][release["tag"].removeprefix("v")] = json.loads(path.read_text())
        items, state = findings(config, snapshot, seen)

        text = _render(items)
        _atomic(watch_dir / "latest.md", text)
        _atomic(seen_path, json.dumps(state, indent=2) + "\n")
        if seen is not None and any(item["kind"] in ("new", "open", "error") for item in items):
            inbox = Path(os.environ.get("NOUS_EVAL_INBOX", config["inbox"]))
            date = datetime.now(timezone.utc).date().isoformat()
            _atomic(inbox / f"{date}-nous-inference-watch.md", text)
        print(text, end="")
        return 0
    except Exception as exc:
        print(f"nous-eval watch: {exc}", file=sys.stderr)
        return 1

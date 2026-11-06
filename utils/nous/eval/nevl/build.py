"""Build comparison engines; check and canary the latest radiance release."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import re
import urllib.request
from pathlib import Path

from . import store
from .candidate import incumbent, load, manifest
from .compare import compare, write
from .guards import UNIT_PATH
from .runner import NOUS_EVAL, plan_run, start

SOURCE = Path("/srv/workspaces/repos/llama.cpp-master")
WORKTREES = Path("/srv/workspaces/repos")
ROCM = "/opt/rocm/core-10.0"
HIP = ["-DGGML_HIP=ON", "-DGPU_TARGETS=gfx1201", f"-DCMAKE_PREFIX_PATH={ROCM}",
       f"-DCMAKE_HIP_COMPILER={ROCM}/llvm/bin/clang"]
BACKENDS = {"vulkan": ["-DGGML_VULKAN=ON"], "hip": HIP, "hip-wmma": [*HIP, "-DGGML_HIP_ROCWMMA_FATTN=ON"]}
REPO = Path(__file__).resolve().parents[4]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(SOURCE), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def resolve_ref(ref: str) -> str:
    git("fetch", "--quiet", "origin")
    return git("rev-parse", "--verify", ref + "^{commit}")


def build_name(sha: str, backend: str, patch: Path | None) -> str:
    """A patch is named by its content too: an edited patch is a different build (council S-05)."""
    if not patch:
        return f"llama-{sha[:9]}-{backend}"
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()[:8]
    return f"llama-{sha[:9]}-{backend}-{patch.stem}-{digest}"


def build(ref: str, backend: str, patch: Path | None = None) -> Path:
    """Build and install one engine; idempotent. Takes ~10-25 minutes."""
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {sorted(BACKENDS)}")
    sha = resolve_ref(ref)
    name = build_name(sha, backend, patch)
    prefix = store.root() / "builds" / name
    if (prefix / "BUILD-OK.json").exists():
        return prefix
    tree = WORKTREES / (f"llama.cpp-{name.removeprefix('llama-')}" if patch else f"llama.cpp-{sha[:9]}")
    if patch:
        _patched_tree(tree, sha, patch)
    elif not tree.exists():
        git("worktree", "add", "--detach", str(tree), sha)
    rpath = "$ORIGIN/../lib" + (f";{ROCM}/lib" if backend.startswith("hip") else "")
    build_dir = tree / f"build-{backend}"
    log = prefix.parent / f"{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    steps = [
        ["cmake", "-S", str(tree), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release",
         f"-DCMAKE_INSTALL_PREFIX={prefix}", f"-DCMAKE_INSTALL_RPATH={rpath}",
         "-DCMAKE_BUILD_WITH_INSTALL_RPATH=OFF", "-DLLAMA_BUILD_TESTS=OFF", *BACKENDS[backend]],
        ["nice", "cmake", "--build", str(build_dir), "-j", "16"],
        ["cmake", "--install", str(build_dir)],
    ]
    with log.open("w") as out:
        for step in steps:
            out.write("$ " + " ".join(step) + "\n")
            out.flush()
            subprocess.run(step, stdout=out, stderr=subprocess.STDOUT, check=True)
    env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
    version = subprocess.run([str(prefix / "bin" / "llama-server"), "--version"], capture_output=True,
                             text=True, env=env).stderr.strip()
    if sha[:7] not in version:
        raise RuntimeError(f"{prefix}/bin/llama-server --version does not name {sha[:7]}: {version!r}")
    (prefix / "BUILD-OK.json").write_text(json.dumps(
        {"sha": sha, "backend": backend, "patch": str(patch) if patch else None, "version": version,
         "ts": time.time()}, indent=2) + "\n")
    return prefix


def _patched_tree(tree: Path, sha: str, patch: Path) -> None:
    """A worktree with `patch` applied, or an error: a failed apply must never
    leave a tree that a retry builds unpatched (council S-05)."""
    marker = tree / ".nevl-patch"
    if tree.exists():
        if marker.exists():
            return
        raise RuntimeError(f"{tree} exists without a recorded patch; remove it: "
                           f"git -C {SOURCE} worktree remove --force {tree}")
    git("worktree", "add", "--detach", str(tree), sha)
    try:
        subprocess.run(["git", "-C", str(tree), "apply", str(patch.resolve())], check=True)
    except subprocess.CalledProcessError:
        git("worktree", "remove", "--force", str(tree))
        raise
    marker.write_text(f"{patch.resolve()}\n")



def build_in_unit(ref: str, backend: str, patch: Path | None) -> int:
    """Long builds run as systemd user units with the unit PATH (ledger M2, M3)."""
    unit = f"nous-eval-build-{backend}-{int(time.time())}"
    argv = [sys.executable, str(NOUS_EVAL), "build", ref, "--backend", backend, "--here"]
    if patch:
        argv += ["--patch", str(patch.resolve())]
    subprocess.run(["systemd-run", "--user", "--unit", unit, "--collect", "-E", f"PATH={UNIT_PATH}",
                    "-E", f"NOUS_EVAL_ROOT={store.root()}", "--", *argv], check=True)
    print(f"started {unit}; follow with: journalctl --user -fu {unit}")
    return 0


def candidate_toml(prefix: Path, backend: str) -> Path:
    """A comparison candidate using the checked-in model preset."""
    path = prefix.parent / f"{prefix.name}.toml"
    lines = [f'label = "{prefix.name.removeprefix("llama-")}"', f'engine = "{prefix}/bin/llama-server"',
             f'preset = "{REPO / "utils" / "nous" / "models.ini"}"',
             "[env]", 'RADV_DEBUG = "nocompute"',
             'VK_DRIVER_FILES = "/opt/mesa-26.2/usr/share/vulkan/icd.d/radeon_icd.json"',
             'LD_LIBRARY_PATH = "/opt/mesa-26.2/usr/lib/x86_64-linux-gnu"']
    if backend != "vulkan":
        lines += ['GPU_MAX_HW_QUEUES = "1"', "[overrides]", 'device = "ROCm0"', 'device-draft = "ROCm0"']
    path.write_text("\n".join(lines) + "\n")
    return path


RADIANCE_REPO = "SlyBase/vllm-sly-radiance"
RADIANCE_API = f"https://api.github.com/repos/{RADIANCE_REPO}/releases/latest"


def latest_radiance_release(payload: dict | None = None) -> dict:
    """Fetch latest release, or normalize a supplied API payload (test seam)."""
    if payload is None:
        request = urllib.request.Request(RADIANCE_API, headers={"Accept": "application/vnd.github+json",
                                                                 "User-Agent": "nous-eval"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    tag = str(payload["tag_name"]).removeprefix("v")
    body = payload.get("body", "")
    match = re.search(r"ghcr\.io/slybase/vllm-sly-radiance:([A-Za-z0-9._-]+)", body)
    if not match:
        raise ValueError(f"release {tag} does not document its radiance image tag")
    image_tag = match.group(1)
    if not image_tag.startswith(tag):
        raise ValueError(f"release {tag} documents unexpected image tag {image_tag}")
    return {"version": tag, "image_tag": image_tag,
            "image_ref": f"ghcr.io/slybase/vllm-sly-radiance:{image_tag}"}


def canary() -> int:
    """Check latest radiance release, export its image, measure it against production, and
    when it passes, run t3 too, so a new release arrives with complete promotion evidence."""
    release = latest_radiance_release()
    production = incumbent()
    label = f"radiance-{release['version']}"
    if production["spec"]["rootfs"].endswith(f"vllm-sly-radiance-{release['image_tag']}"):
        print(f"production already runs {release['image_ref']}")
        return 0
    record = store.root() / "canary" / f"{label}.json"
    if record.exists():
        print(f"canary for {release['image_ref']} already ran: {record}")
        return 0
    rootfs = subprocess.run(["/usr/local/bin/nous-serve", "export", release["image_ref"]],
                            capture_output=True, text=True, check=True).stdout.strip()
    candidate_path = store.root() / "canary" / "candidates" / f"{label}.toml"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(f'kind = "serve"\nlabel = "{label}"\nspec = "{production["spec_source"]}"\n'
                              f'ready_timeout_s = 1800\n\n[overrides]\nrootfs = "{rootfs}"\n')
    candidate = load(candidate_path)
    runs = {}
    for tier in ("canary", "t3"):
        run = store.Run.create(plan_run(tier, [production, candidate]))
        runs[tier] = run.run_id
        status = start(run)
        if not run.done():
            return status or 1
        report = compare(run, "incumbent", label)
        text = write(run, report)
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"image_ref": release["image_ref"], "run_id": runs["canary"],
                                      "t3_run_id": runs.get("t3"), "verdict": report["verdict"],
                                      "candidate": str(candidate_path)}, indent=2) + "\n")
        (record.parent / f"latest-{tier}.md").write_text(text)
        print(text)
        if tier == "canary" and report["verdict"] != "pass":
            print(f"Candidate spec: {candidate_path}; canary did not pass, so t3 was not run.")
            return status
    print(f"Candidate spec: {candidate_path}")
    print(f"Next: `./nous-eval promote {label} --run {runs['canary']} --run {runs['t3']}`.")
    return status


def promote(label: str, run_ids: list[str]) -> int:
    """Check the evidence, then print the steps to make `label` production (ledger M11, M19).

    Evidence is a set of runs, each finished ok against the incumbent and measuring
    its tier's full workload set. Together they cover speed, context and agents (a
    t2 or canary run whose compare passes) and accuracy (a t3 run whose compare does
    not fail: one sample per LCB item flips too often for 258 items to certify a
    4-point margin, but a clear loss fails; council F-11). The candidate is
    identical in all of them, and each run's incumbent is still production."""
    snapshots, tiers = [], set()
    for run_id in run_ids:
        run = store.Run.open(run_id)
        plan = run.plan
        report = run.read_json(f"compare.incumbent.{label}.json")
        if report is None:
            print(f"{run_id}: no compare of {label} against incumbent; run `nous-eval compare {run_id}`")
            return 1
        if (run.done() or {}).get("status") != "ok":
            print(f"{run_id}: the run did not finish ok")
            return 1
        needed = ("pass", "inconclusive") if plan["tier"] == "t3" else ("pass",)
        if report["verdict"] not in needed:
            print(f"{run_id}: verdict {report['verdict']}; a {plan['tier']} run needs {' or '.join(needed)}")
            return 1
        measured = [w["name"] for w in plan["workloads"]]
        if sorted(measured) != sorted(plan["tier_workloads"]):
            print(f"{run_id}: measured {measured} of tier {plan['tier']}'s {plan['tier_workloads']}")
            return 1
        recorded, now = _identity(run.read_json("manifest.incumbent.json")), production_identity()
        if recorded != now:
            print(f"{run_id}: production has changed since this run ({_changed(recorded, now)}); measure again")
            return 1
        snapshots.append((plan["candidates"][label], _identity(run.read_json(f"manifest.{label}.json"))))
        tiers.add(plan["tier"])
    if not tiers & {"t2", "canary"} or "t3" not in tiers:
        print(f"promotion needs passing t2 or canary (speed, context, agents) and t3 (accuracy) runs; got {sorted(tiers)}")
        return 1
    candidate, measured = snapshots[0]
    if any(s != snapshots[0] for s in snapshots[1:]):
        print(f"{label} differs between the runs; evidence must be about one candidate")
        return 1
    now = _identity(manifest(candidate))
    if measured != now:  # council S-08
        print(f"{label} changed after it was measured ({_changed(measured, now)}); measure again")
        return 1
    if candidate["kind"] == "serve":
        production_spec = Path(candidate["spec_source"])
        print(f"""Evidence: {', '.join(run_ids)} pass for {label}.
Review the frozen spec in runs/*/plan.json and candidate manifest first.
Promotion (operator-reviewed, not applied automatically):
  edit {production_spec}: rootfs = "{candidate['spec']['rootfs']}" (preserve all measured knobs)
  update {REPO}/utils/nous/serve/production.toml to the same spec
  sudo -n install -m 644 {REPO}/utils/nous/serve/production.toml /etc/nous-inference/serve.toml
  sudo -n systemctl restart llama.service
  nous-eval run t1 --incumbent
Rollback: restore the previous spec rootfs from the incumbent manifest/plan.json,
install it at /etc/nous-inference/serve.toml, and restart llama.service.""")
        return 0
    if candidate["kind"] != "llama-router":
        print(f"{label} is a {candidate['kind']} candidate and cannot be promoted.")
        return 1
    current = incumbent()
    engine_dir = Path(candidate["engine"]).parent.parent
    _, sha, variant = engine_dir.name.split("-", 2)
    target = Path("/opt") / f"llama.cpp-{variant}-{sha}"
    print(f"""Evidence: {', '.join(run_ids)} pass for {label}.
Legacy llama.cpp build promotion is not supported for the production service.""")
    return 1


def rollback() -> int:
    """Print manual rollback instructions using the prior incumbent frozen by the canary run."""
    records = sorted((store.root() / "canary").glob("*.json"), key=lambda path: path.stat().st_mtime,
                     reverse=True)
    previous = None
    for record in records:
        data = json.loads(record.read_text())
        if not data.get("run_id"):
            continue
        try:
            previous = store.Run.open(data["run_id"]).plan["candidates"]["incumbent"]["spec"]["rootfs"]
        except (KeyError, OSError, ValueError):
            continue
        break
    if previous is None:
        print("no canary run records a prior production spec; restore the previous spec from its backup")
        return 1
    print(f"""Restore the production spec recorded as incumbent before this canary:
  edit {REPO}/utils/nous/serve/production.toml and /etc/nous-inference/serve.toml to set rootfs = "{previous}"
  sudo -n install -m 644 {REPO}/utils/nous/serve/production.toml /etc/nous-inference/serve.toml
  sudo -n systemctl restart llama.service
  nous-eval run t1 --incumbent""")
    return 0


def production_identity() -> dict:
    """Production's manifest now, without per-run block records."""
    return _identity(manifest(incumbent()))


def _identity(manifest_: dict | None) -> dict | None:
    """A manifest without its per-run block records."""
    return None if manifest_ is None else {k: v for k, v in manifest_.items() if k != "blocks"}


def _changed(before: dict | None, after: dict | None) -> str:
    """The manifest keys that differ, so the operator sees what moved (kernel, engine, model)."""
    before, after = before or {}, after or {}
    return ", ".join(sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k)))

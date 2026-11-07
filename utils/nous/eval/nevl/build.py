"""Build comparison engines; check and canary the latest radiance release."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import store
from .candidate import CandidateError, incumbent, load, manifest
from .compare import compare, pair_complete, write
from .guards import UNIT_PATH
from .runner import NOUS_EVAL, plan_run, start

SOURCE = Path("/srv/workspaces/repos/llama.cpp-master")
WORKTREES = Path("/srv/workspaces/repos")
ROCM = "/opt/rocm/core-10.0"
HIP = ["-DGGML_HIP=ON", "-DGPU_TARGETS=gfx1201", f"-DCMAKE_PREFIX_PATH={ROCM}",
       f"-DCMAKE_HIP_COMPILER={ROCM}/llvm/bin/clang"]
BACKENDS = {"vulkan": ["-DGGML_VULKAN=ON"], "hip": HIP, "hip-wmma": [*HIP, "-DGGML_HIP_ROCWMMA_FATTN=ON"]}
CANARY_HOME_ROOT = Path("/srv/workspaces/vllm-cache")
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
    """Measure the latest radiance release against production, then run t3 when the canary
    passes, so a new release arrives with complete promotion evidence.

    The record under canary/ saves each stage before it starts (atomically: a power loss
    mid-write keeps the previous record), so a timer firing after a reboot resumes the
    same runs, and grades a run the reboot cut between its lease and grading (council
    S-02). A canary that does not pass is measured once more in a new run of the same
    export: ROCm draws one of two speeds per process (ledger M44), which can slow a
    candidate's blocks or swing its A/A (council O-05). A second non-pass, or a finished
    t3, makes the record terminal. A stage that ends unfinished (a failed preflight, a
    stopped lease) is noted as `blocked` for the watch (council O-14)."""
    try:
        release = latest_radiance_release()
        production = incumbent()
    except CandidateError as error:
        print(f"canary requires nous-serve production: {error}")
        return 1
    label = f"radiance-{release['version']}"
    if production["spec"]["rootfs"].endswith(f"vllm-sly-radiance-{release['image_tag']}"):
        print(f"production already runs {release['image_ref']}")
        return 0
    record = store.root() / "canary" / f"{label}.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(record.read_text()) if record.exists() else {"image_ref": release["image_ref"], "attempts": 0}
    # A record from before resumable canaries counts no attempts; its canary run is one (release audit)
    data.setdefault("attempts", 1 if data.get("run_id") else 0)

    def save(**changes) -> None:
        data.update(changes)
        store.write_durable(record, json.dumps(data, indent=2) + "\n")

    if data.get("terminal"):
        print(f"canary for {release['image_ref']} is terminal: {data['verdict']}")
        return 0 if data["verdict"] == "pass" else 1
    if not data.get("candidate"):
        rootfs = subprocess.run(["/usr/local/bin/nous-serve", "export", release["image_ref"]],
                                capture_output=True, text=True, check=True).stdout.strip()
        candidate_path = store.root() / "canary" / "candidates" / f"{label}.toml"
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        home = CANARY_HOME_ROOT / Path(rootfs).name / "home"  # made below on every pass
        production_spec = candidate_path.with_suffix(".production.toml")  # the record is gone at the next stop
        # On disk, with every directory entry on the way (candidates/ was just made), before the
        # record names them: after a power loss the stage resumes (release audit)
        store.write_durable(production_spec, _toml_spec(production["spec"]))
        store.write_durable(candidate_path, f'kind = "serve"\nlabel = "{label}"\nspec = "{production_spec}"\n'
                            f'ready_timeout_s = 1800\n\n[overrides]\nrootfs = "{rootfs}"\nhome = "{home}"\n')
        os.sync()
        save(candidate=str(candidate_path), home=str(home))
    # An empty compile-cache home: made on every pass rather than made durable, so a power loss
    # that took the directory after the record named it cannot stop the stage resuming (release audit).
    # Records from before resumable canaries name no home; their candidates used production's.
    home = data.get("home") or tomllib.loads(Path(data["candidate"]).read_text()).get("overrides", {}).get("home")
    if home:
        Path(home).mkdir(parents=True, exist_ok=True)
    candidate = load(Path(data["candidate"]))
    for tier, key in (("canary", "run_id"), ("t3", "t3_run_id")):
        if not data.get(key):
            attempts = data["attempts"] + (tier == "canary")
            save(attempts=attempts, **{key: store.Run.create(plan_run(tier, [production, candidate])).run_id})
        run = store.Run.open(data[key])
        save(blocked=None)
        # Under the run's lock: a finished run is graded, a stopped one (finished or not) left alone
        status = start(run, automatic=True)
        stopped = (run.path / "stopped.json").exists()
        if stopped or not run.done():
            why = ("was stopped; continue with: nous-eval resume " + run.run_id
                   if stopped else f"did not finish (exit {status})")
            save(blocked=f"{tier} run {run.run_id} {why} at "
                         f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M}Z; preflight and lease output: "
                         "`journalctl --user -u nous-eval-canary`")
            return status or 1
        report = compare(run, "incumbent", label)
        text = write(run, report)
        (record.parent / f"latest-{tier}.md").write_text(text)
        print(text)
        if tier == "canary" and report["verdict"] != "pass":
            save(unstable=report.get("unstable"), canary_verdict=report["verdict"], verdict=report["verdict"])
            if data["attempts"] >= 2:
                save(terminal=True)
                print(f"canary {report['verdict']} after {data['attempts']} attempts; terminal")
            else:
                save(run_id=None)
                print(f"canary {report['verdict']}; the next timer run measures it once more")
            return 1
        save(**{f"{tier}_verdict": report["verdict"], "verdict": report["verdict"]})
        if report["verdict"] != "pass":
            save(terminal=True)
            print(f"Candidate spec: {data['candidate']}; {tier} verdict {report['verdict']}, not promotable.")
            return 1
    save(terminal=True)
    print(f"Candidate spec: {data['candidate']}")
    print(f"Next: `./nous-eval promote {label} --run {data['run_id']} --run {data['t3_run_id']}`.")
    return 0


def promote(label: str, run_ids: list[str]) -> int:
    """Check promotion evidence. t3's replicated paired interval makes pass a real
    non-inferiority claim at the configured margin."""
    snapshots, tiers = [], set()
    for run_id in run_ids:
        run = store.Run.open(run_id)
        plan = run.plan
        report = run.read_json(f"compare.incumbent.{label}.json")
        if report is None:
            print(f"{run_id}: no compare of {label} against incumbent; run `nous-eval compare {run_id}`")
            return 1
        if report.get("evidence") != run.evidence():
            print(f"{run_id}: its compare of {label} predates the run's current rows; "
                  f"run `nous-eval compare {run_id} --a incumbent --b {label}`")
            return 1
        if not pair_complete(run.done() or {}, "incumbent", label):
            print(f"{run_id}: the run did not finish ok for incumbent and {label}")
            return 1
        needed = ("pass",)
        if report["verdict"] not in needed:
            print(f"{run_id}: verdict {report['verdict']}; a {plan['tier']} run needs pass")
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
        spec_path = store.root() / "promote" / f"{label}.toml"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            old = SERVE_SPEC.read_text()
        except OSError:
            old = ""
        annotated = _annotated_spec(old, candidate["spec"]) if old else None
        text = annotated or _toml_spec(candidate["spec"])
        try:
            loads_back = tomllib.loads(text) == candidate["spec"]
        except tomllib.TOMLDecodeError:
            loads_back = False
        if not loads_back:  # release audit: never print install steps for a spec nous-serve cannot load
            print(f"{label}'s spec does not serialize to TOML that loads back as itself; not promoting")
            return 1
        spec_path.write_text(text)
        print("".join(difflib.unified_diff(old.splitlines(True), spec_path.read_text().splitlines(True),
                                            fromfile=str(SERVE_SPEC), tofile=str(spec_path))))
        if annotated is None:
            print(f"{spec_path} is generated without {SERVE_SPEC}'s comments; carry over those still true.")
        archive = _archive_path()
        print(f"""Evidence: {', '.join(run_ids)} pass for {label}.
Review the frozen spec and candidate manifest first.
Promotion (operator-reviewed, not applied automatically):
  sudo -n install -D -m 644 {SERVE_SPEC} {archive}
  sudo -n install -D -m 644 {spec_path} {SERVE_SPEC}
  install -m 644 {spec_path} {REPO}/utils/nous/serve/production.toml
  sudo -n systemctl restart llama.service
  sudo -n llama-speedcheck --calibrate   # idle, 3 min after it answers (refused while settling)
  nous-eval run t1 --incumbent""")
        return 0
    if candidate["kind"] != "llama-router":
        print(f"{label} is a {candidate['kind']} candidate and cannot be promoted.")
        return 1
    print(f"""Evidence: {', '.join(run_ids)} pass for {label}.
Legacy llama.cpp build promotion is not supported for the production service.""")
    return 1


SERVE_SPEC = Path("/etc/nous-inference/serve.toml")
HISTORY_DIR = Path("/etc/nous-inference/history")


def _archive_path() -> Path:
    """A history name later than every existing one: never the rollback source, and the
    archived live spec sorts as the newest deployment (release audit)."""
    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    for path in HISTORY_DIR.glob("serve-*.toml"):
        try:
            seen = datetime.strptime(path.stem, "serve-%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        stamp = max(stamp, seen + timedelta(seconds=1))
    return HISTORY_DIR / f"serve-{stamp:%Y%m%dT%H%M%SZ}.toml"


def _toml_value(v) -> str:
    """TOML basic strings take JSON's escapes except surrogate pairs, so non-ASCII stays literal;
    JSON leaves DEL raw, which TOML forbids (release audit)."""
    return json.dumps(v, ensure_ascii=False).replace("\x7f", "\\u007f")


def _toml_spec(spec: dict) -> str:
    value = _toml_value
    rows = [f"{key} = {value(spec[key])}" for key in ("rootfs", "served_model_name", "home", "args")]
    for section in ("env", "mounts"):
        rows.extend(["", f"[{section}]"])
        rows.extend(f"{value(k)} = {value(v)}" for k, v in sorted(spec[section].items()))
    return "\n".join(rows) + "\n"


def _annotated_spec(text: str, spec: dict) -> str | None:
    """`spec` written over the annotated spec `text`: only lines whose value changed are
    rewritten, keeping their comments, the record of why each knob is set (council F-09); a
    changed list is merged line by line (_merged_list); a removed key goes with the comment
    above it. None when `text` has a value it cannot read or the result would not load back
    as `spec`."""
    value = _toml_value
    want = {"": {k: spec[k] for k in ("rootfs", "served_model_name", "home", "args")},
            "env": spec["env"], "mounts": spec["mounts"]}
    written = {name: set() for name in want}
    out: list[str] = []
    sections = []

    def close(name: str) -> None:
        """Append the section's keys the old file lacked, before its trailing blank lines."""
        tail = []
        while out and not out[-1].strip():
            tail.append(out.pop())
        for key in [k for k in want.get(name, {}) if k not in written[name]]:
            out.append(f"{value(key) if name else key} = {value(want[name][key])}")
            written[name].add(key)
        out.extend(reversed(tail))

    lines = iter(text.splitlines())
    section = ""
    for line in lines:
        header = re.fullmatch(r"\s*\[\s*([^\]]+?)\s*\]\s*(?:#.*)?", line)
        if header:
            close(section)
            section = header.group(1).strip('"')
            sections.append(section)
            out.append(line)
            continue
        match = re.fullmatch(r'(\s*)("(?:[^"\\]|\\.)*"|[A-Za-z0-9_-]+)\s*=\s*(.*)', line)
        if not match or section not in want:
            out.append(line)
            continue
        indent, raw_key, rest = match.groups()
        block = [rest]
        try:
            key = next(iter(tomllib.loads(f"{raw_key} = 0")))
            while True:  # a value may span lines however it is wrapped: read until it parses
                try:
                    old = tomllib.loads("k = " + "\n".join(block))["k"]
                    break
                except tomllib.TOMLDecodeError:
                    block.append(next(lines))
        except (StopIteration, tomllib.TOMLDecodeError):
            return None
        if key not in want[section]:
            while out and out[-1].lstrip().startswith("#"):
                out.pop()
            continue
        new = want[section][key]
        written[section].add(key)
        if old == new:
            out.append(line)
            out.extend(block[1:])
        elif isinstance(new, list):
            rows = _merged_list(rest, block[1:], old, new, value)
            if rows:
                out.extend([line, *rows])
            else:
                out.append(f"{indent}{raw_key} = [")
                out.extend(f"{indent}  {value(item)}," for item in new)
                out.append(f"{indent}]")
        else:
            comment = re.fullmatch(r'("(?:[^"\\]|\\.)*"|\'[^\']*\'|[^\s#]+)(\s*#.*)?', rest)
            out.append(f"{indent}{raw_key} = {value(new)}{(comment and comment.group(2)) or ''}")
    close(section)
    for name in want:
        if name and name not in sections and want[name]:
            out.extend(["", f"[{name}]"])
            close(name)
    merged = "\n".join(out) + "\n"
    try:
        same = tomllib.loads(merged) == tomllib.loads(_toml_spec(spec))
    except tomllib.TOMLDecodeError:
        return None
    return merged if same else None


def _merged_list(rest: str, body: list[str], old: list, new: list, value) -> list[str] | None:
    """The lines after `key = [` of a list rewritten from `old` to `new` line by line, so the
    comments in it, the reasons for each flag, survive a change (council F-09): a changed
    element re-renders only its own line, keeping that line's comment; an added one joins the
    line of the element before it; a line left with no elements goes, with the comments above
    it. None for a layout this does not read, such as elements on a bracket's line."""
    if not old or not body or not re.fullmatch(r"\[\s*(?:#.*)?", rest.strip()) \
            or not re.fullmatch(r"\]\s*(?:#.*)?", body[-1].strip()):
        return None
    lines = []  # (line, its elements, the code before its comment, the comment)
    owner = []  # the line index of each old element
    for line in body[:-1]:
        for cut in [i for i, c in enumerate(line) if c == "#"] + [len(line)]:
            try:  # the first `#` outside a string is where the comment starts
                items = tomllib.loads("x = [\n" + line[:cut] + "\n]")["x"]
                break
            except tomllib.TOMLDecodeError:
                continue
        else:
            return None
        owner.extend([len(lines)] * len(items))
        lines.append((line, items, line[:cut], line[cut:]))
    if [item for _, items, _, _ in lines for item in items] != old:
        return None
    given: list[list] = [[] for _ in lines]
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                given[owner[i]].append(new[j])
        elif j2 > j1:  # owners only grow, so the lines still hold `new` in order
            given[owner[i1] if i2 > i1 else owner[max(i1 - 1, 0)]].extend(new[j1:j2])
    out: list[str] = []
    for (line, items, code, comment), mine in zip(lines, given):
        if mine == items:  # unchanged, or a comment or blank line
            out.append(line)
        elif not mine:
            while out and out[-1].lstrip().startswith("#"):
                out.pop()
        else:
            lead = code[:len(code) - len(code.lstrip())]
            gap = code[len(code.rstrip()):] if comment else ""
            out.append(f"{lead}{', '.join(value(item) for item in mine)},{gap}{comment}")
    out.append(body[-1])
    return out


def rollback() -> int:
    """Print commands to restore the newest archived production spec that differs."""
    try:
        current = SERVE_SPEC.read_text()
    except OSError as exc:
        print(f"cannot read current production spec {SERVE_SPEC}: {exc}")
        return 1
    histories = sorted(HISTORY_DIR.glob("serve-*.toml"), reverse=True)
    for target in histories:
        text = target.read_text()
        if text == current:
            continue
        print("".join(difflib.unified_diff(current.splitlines(True), text.splitlines(True),
                                            fromfile=str(SERVE_SPEC), tofile=str(target))))
        archive = _archive_path()
        print(f"""Rollback:
  sudo -n install -D -m 644 {SERVE_SPEC} {archive}
  sudo -n install -D -m 644 {target} {SERVE_SPEC}
  install -m 644 {target} {REPO}/utils/nous/serve/production.toml
  sudo -n systemctl restart llama.service
  sudo -n llama-speedcheck --calibrate   # idle, 3 min after it answers (refused while settling)
  nous-eval run t1 --incumbent""")
        return 0
    print(f"No differing archived production spec found in {HISTORY_DIR}; see docs/nous-inference.md rollback section.")
    return 1


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

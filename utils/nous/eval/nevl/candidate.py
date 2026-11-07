"""Candidates: what to serve and how.

A candidate TOML is resolved once, when a run is planned, into a
self-contained JSON-able dict that is snapshotted into plan.json (ledger M10):
later edits to preset files, candidate files or the unit cannot change a run.

kind = "llama-router" (default): llama.cpp and a preset section.
kind = "serve": a nous-serve spec, resolved and snapshotted into the plan.
kind = "command": a foreground OpenAI-compatible process.
All kinds accept a label and request; overrides depend on kind.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import tomllib
from pathlib import Path

PRODUCTION_UNIT = "llama.service"
MODELS_ROOT = Path("/srv/models")
LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]{0,119}$")  # vLLM keys are long: speculative-config.num_speculative_tokens
SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*$")
MODEL_KEYS = ("model", "mmproj", "model-draft")


class CandidateError(ValueError):
    pass


def load(path: Path, overrides: dict | None = None) -> dict:
    """A candidate file, optionally with overrides (`run --set`).

    Overrides become part of the label (tip-vulkan.ubatch-size-2048), so two
    settings of one file never share a label in a run or a comparison."""
    path = Path(path)
    raw = tomllib.loads(path.read_text())
    if overrides:
        raw.setdefault("overrides", {}).update(overrides)
        suffix = ".".join(f"{key}-{value}" for key, value in sorted(overrides.items()))
        raw["label"] = re.sub(r"[^a-z0-9._-]", "-", f"{raw.get('label', path.stem)}.{suffix}".lower())
    return resolve(raw, source=str(path), default_label=path.stem)


def resolve(raw: dict, *, source: str, default_label: str) -> dict:
    kind = raw.get("kind", "llama-router")
    label = raw.get("label", default_label)
    if not LABEL.match(label):
        raise CandidateError(f"bad label {label!r}: use [a-z0-9._-]")
    env = {str(k): str(v) for k, v in raw.get("env", {}).items()}
    common = {"kind": kind, "label": label, "source": source, "env": env,
              "request": raw.get("request", {})}
    if kind == "serve":
        spec_path = Path(raw["spec"])
        try:
            serve = _serve_module()
            spec = serve.load(spec_path)
        except Exception as exc:
            raise CandidateError(f"{label}: cannot load nous-serve spec {spec_path}: {exc}") from exc
        overrides = raw.get("overrides", {})
        base_env = _image_environment(spec)
        for key, value in overrides.items():
            if key == "rootfs":
                spec["rootfs"] = Path(value)
            elif key == "served_model_name":
                spec[key] = str(value)
            elif key == "home":
                spec[key] = Path(value)
            elif key.isupper():
                if key not in spec["env"] and key not in base_env:
                    raise CandidateError(f"{label}: {key} is absent from spec and image environment")
                spec["env"][key] = str(value)
            else:
                spec["args"] = _override_argv(spec["args"], {key: value})
        _check_start(label, spec["args"])
        # nous-serve.load() validates paths and owned flags; preserve its normalized JSON shape.
        resolved = {k: str(v) if isinstance(v, Path) else v for k, v in spec.items()}
        return {**common, "spec": resolved, "spec_source": str(spec_path),
                "model": spec["served_model_name"],
                "ready_timeout_s": int(raw.get("ready_timeout_s", 1800))}
    if kind == "command":
        start = _override_argv([str(x) for x in raw["start"]], raw.get("overrides", {}))
        _check_start(label, start)
        return {**common,
                "start": start, "stop": [str(x) for x in raw.get("stop", [])],
                "base_url": raw.get("base_url", "http://127.0.0.1:18737"),
                "model": raw["model"], "ready_timeout_s": int(raw.get("ready_timeout_s", 900)),
                "identity": [str(x) for x in raw.get("identity", [])],
                "model_files": [str(x) for x in raw.get("model_files", [])]}
    if kind != "llama-router":
        raise CandidateError(f"{label}: unknown kind {kind!r}")
    preset_text, section = derive_preset(Path(raw["preset"]).read_text(), raw.get("section"),
                                         raw.get("overrides", {}))
    return {**common, "engine": str(Path(raw["engine"]).resolve()), "preset_source": str(raw["preset"]),
            "preset_text": preset_text, "section": section, "model": section,
            "args": [str(x) for x in raw.get("args", [])],
            "ready_timeout_s": int(raw.get("ready_timeout_s", 600))}


def _serve_module():
    import importlib.util
    from importlib.machinery import SourceFileLoader
    path = Path(__file__).resolve().parents[2] / "serve" / "nous-serve"
    loader = SourceFileLoader("nevl_nous_serve", str(path))
    module_spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(module_spec)
    loader.exec_module(module)
    return module


def _image_environment(spec: dict) -> dict:
    sidecar = json.loads((Path(spec["rootfs"]) / ".nous-serve-image.json").read_text())
    return dict(item.split("=", 1) for item in sidecar.get("env", []))


def incumbent(show: str | None = None) -> dict:
    """Production as it runs now, read from the live nous-serve unit (ledger M20): the spec
    bytes the running invocation loaded, which `nous-serve run --record` leaves for exactly its
    lifetime (ledger M60); with none (stopped, or a lease) the spec the next start loads."""
    if show is None:
        show = subprocess.run(["systemctl", "show", PRODUCTION_UNIT, "-p", "ExecStart"],
                              capture_output=True, text=True, check=True).stdout
    exec_line = next((line for line in show.splitlines() if line.startswith("ExecStart=")), "")
    match = re.search(r"argv\[\]=(.*?) ;", exec_line)
    if not match:
        raise CandidateError(f"cannot parse ExecStart for {PRODUCTION_UNIT}: {exec_line!r}")
    argv = shlex.split(match.group(1))
    if (len(argv) not in (5, 7) or argv[:2] != ["/usr/local/bin/nous-serve", "run"] or argv[3] != "--port"
            or argv[5:6] not in ([], ["--record"])):
        raise CandidateError(f"{PRODUCTION_UNIT} ExecStart is not nous-serve run SPEC --port N [--record PATH]")
    spec = argv[6] if len(argv) == 7 and Path(argv[6]).exists() else argv[2]
    return resolve({"kind": "serve", "label": "incumbent", "spec": spec},
                   source=f"live {PRODUCTION_UNIT}", default_label="incumbent")





def _check_start(label: str, argv: list[str]) -> None:
    """Refuse recipe flags that are only safe beside a setting the candidate changed.

    The vLLM fork's quickstart pairs --skip-mm-profiling with images off. With
    images on, no VRAM is reserved for the vision encoder, and at 0.98 memory
    utilisation a large screenshot kills the engine mid-run (ledger M43)."""
    flag = "--limit-mm-per-prompt.image"
    images = argv[argv.index(flag) + 1] if flag in argv else None
    if "--skip-mm-profiling" in argv and images != "0":
        raise CandidateError(f"{label}: --skip-mm-profiling reserves no VRAM for the vision encoder; "
                             f"drop it or set {flag} 0")


def _override_argv(argv: list[str], overrides: dict) -> list[str]:
    """Apply `run --set` to a command candidate's start argv (see the module doc).

    `--KEY VALUE` gets its value replaced; a bare `--KEY` is a boolean switch that
    `false` removes; `-e KEY=...` gets its value replaced. A key not in the argv is
    appended: `true`/`false` as `--KEY`/`--no-KEY` (argparse booleans), else `--KEY VALUE`."""
    out = list(argv)
    for key, value in overrides.items():
        value = str(value)
        flag = f"--{key}"
        if flag in out:
            i = out.index(flag)
            switch = i + 1 == len(out) or out[i + 1].startswith("--")
            if not switch:
                out[i + 1] = value
            elif value == "false":
                del out[i]
            elif value != "true":
                raise CandidateError(f"{flag} is a switch in start; --set {key}=true or false")
            continue
        env = [i for i in range(1, len(out)) if out[i - 1] == "-e" and out[i].startswith(f"{key}=")]
        if env:
            out[env[0]] = f"{key}={value}"
        elif key.isupper():
            # An environment knob such as RADIANCE_CACTUS_DELTA appended as a flag would
            # crash the server or, worse, be ignored; its default must be in start.
            raise CandidateError(f"{key} looks like an environment variable but start has no -e {key}=...; "
                                 f"add it with its default first")
        elif value in ("true", "false"):
            out.append(flag if value == "true" else f"--no-{key}")
        else:
            out += [flag, value]
    return out


def derive_preset(text: str, section: str | None, overrides: dict) -> tuple[str, str]:
    """Keep the top-level lines, `[*]` and one model section; apply overrides to that section."""
    head: list[str] = []
    blocks: dict[str, list[str]] = {}
    current = head
    for line in text.splitlines():
        match = SECTION.match(line)
        if match:
            current = blocks.setdefault(match.group(1).strip(), [])
        elif line.strip() and not line.lstrip().startswith((";", "#")):
            current.append(line)
    if section is None:
        section = next((name for name, lines in blocks.items()
                        if name != "*" and any(_key(l) == "load-on-startup" and _value(l) == "true"
                                               for l in lines)), None)
        if section is None:
            raise CandidateError("preset has no load-on-startup section; set `section`")
    if section not in blocks:
        raise CandidateError(f"preset has no section [{section}]")
    lines = list(blocks[section])
    for key, value in overrides.items():
        value = str(value).lower() if isinstance(value, bool) else str(value)
        lines = [l for l in lines if _key(l) != key] + [f"{key} = {value}"]
    out = head + (["", "[*]", *blocks["*"]] if "*" in blocks else []) + ["", f"[{section}]", *lines]
    return "\n".join(out).strip() + "\n", section


def _key(line: str) -> str:
    return line.partition("=")[0].strip()


def _value(line: str) -> str:
    return line.partition("=")[2].split(";")[0].strip().lower()


def preset_model_files(preset_text: str) -> list[Path]:
    files = []
    for line in preset_text.splitlines():
        if _key(line) in MODEL_KEYS:
            path = Path(line.partition("=")[2].split(";")[0].strip().strip('"'))
            files.append(path if path.is_absolute() else MODELS_ROOT / path)
    return files


def process_env(candidate: dict) -> dict:
    env = {**os.environ, **candidate["env"]}
    if candidate["kind"] == "llama-router":
        lib = str(Path(candidate["engine"]).parent.parent / "lib")
        env["LD_LIBRARY_PATH"] = lib + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    return env


def manifest(candidate: dict) -> dict:
    """Exact identity of everything that can change a measurement."""
    out = {"label": candidate["label"], "kind": candidate["kind"], "env": candidate["env"],
           "kernel": platform.uname().release, "request": candidate["request"]}
    if candidate["kind"] == "serve":
        spec = candidate["spec"]
        module = _serve_module()
        spec_obj = dict(spec, rootfs=Path(spec["rootfs"]), home=Path(spec["home"]))
        identity = module.identity(spec_obj)
        out["nous_serve"] = {"identity": identity,
                             "binary": _fingerprint(Path("/usr/local/bin/nous-serve"), whole=True)}
        files = set()
        for value in spec["args"]:
            for inside, host in spec["mounts"].items():
                if value == inside or value.startswith(inside.rstrip("/") + "/"):
                    files.add(str(Path(host) / value[len(inside):].lstrip("/")))
        out["model_files"] = [_fingerprint(Path(p)) for p in sorted(files)]
        out["spec"] = spec
        return out
    if candidate["kind"] == "command":
        out["argv"] = candidate["start"]
        if candidate["identity"]:
            out["identity"] = subprocess.run(candidate["identity"], capture_output=True, text=True,
                                             check=True).stdout.strip()
        out["model_files"] = [_fingerprint(Path(p)) for p in candidate["model_files"]]
        return out
    engine = Path(candidate["engine"])
    out["engine"] = _fingerprint(engine, whole=True)
    version = subprocess.run([str(engine), "--version"], capture_output=True, text=True,
                             env=process_env(candidate)).stderr
    # Only the version lines: the log lines around them carry timestamps, and an
    # identity that changes on every call fails the next block (ledger M41).
    out["engine_version"] = "\n".join(line for line in version.splitlines()
                                      if line.startswith(("version:", "built with")))
    out["libraries"] = [_fingerprint(p, whole=True)
                        for p in sorted((engine.parent.parent / "lib").glob("lib*.so*")) if not p.is_symlink()]
    out["preset_sha256"] = hashlib.sha256(candidate["preset_text"].encode()).hexdigest()
    out["model_files"] = [_fingerprint(p) for p in preset_model_files(candidate["preset_text"])]
    icd = candidate["env"].get("VK_DRIVER_FILES")
    if icd:
        out["vulkan_icd"] = json.loads(Path(icd).read_text()).get("ICD", {}).get("library_path")
    return out


def _fingerprint(path: Path, whole: bool = False) -> dict:
    """sha256 of a file (whole, or first+last 16 MiB for weights); directories recurse."""
    if path.is_dir():
        return {"path": str(path), "files": [_fingerprint(p) for p in sorted(path.rglob("*")) if p.is_file()]}
    size = path.stat().st_size
    digest = hashlib.sha256()
    window = 16 << 20
    with path.open("rb") as f:
        if whole or size <= 2 * window:
            for block in iter(lambda: f.read(1 << 20), b""):
                digest.update(block)
        else:
            digest.update(f.read(window))
            f.seek(size - window)
            digest.update(f.read(window))
    return {"path": str(path), "size": size, "sha256": digest.hexdigest(), "whole": whole or size <= 2 * window}

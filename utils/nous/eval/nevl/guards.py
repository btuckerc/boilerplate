"""Preflight guards. Each guard exists because a past mistake (ledger.toml) cost a run.

A guard takes a Host (every path it reads, so tests point it at fake trees) and
returns (status, detail) with status in ok | warn | fail | skip.
when = "host":  checked by `nous-eval preflight` and before taking a lease
when = "lease": checked inside the lease, before the first server starts
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import tomllib
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import store
from .candidate import PRODUCTION_UNIT, incumbent
from .sandbox import run_python

# The PATH every nous-eval systemd user unit sets (ledger M2).
UNIT_PATH = "/home/tux/.local/share/mise/shims:/home/tux/.local/bin:/usr/local/bin:/usr/bin:/bin"
LEASE_UNIT = "llama-yield-gpu.service"
CONFIG = Path(__file__).resolve().parents[1] / "tiers.toml"


@dataclass
class Host:
    drm: Path = Path("/sys/class/drm")
    cgroup_root: Path = Path("/sys/fs/cgroup")
    proc: Path = Path("/proc")
    production_pid: int | None = None  # None: llama.service's MainPID
    loadavg: Path = Path("/proc/loadavg")
    meminfo: Path = Path("/proc/meminfo")
    mounts: Path = Path("/proc/self/mounts")
    eval_root: Path = field(default_factory=store.root)
    system_root: Path = Path("/")
    unit_path: str = UNIT_PATH
    config: dict = field(default_factory=lambda: tomllib.loads(CONFIG.read_text())["guards"])
    plan: dict | None = None  # the run about to take the GPU; None: production only
    boot: Path = Path("/boot")
    kernel: str = field(default_factory=lambda: os.uname().release)


@dataclass
class Guard:
    id: str
    when: str
    mistakes: tuple
    check: Callable[[Host], tuple[str, str]]


REGISTRY: dict[str, Guard] = {}


def guard(guard_id: str, when: str = "host", mistakes: tuple = ()):
    def register(fn):
        REGISTRY[guard_id] = Guard(guard_id, when, mistakes, fn)
        return fn
    return register


def run(when: str, host: Host | None = None) -> list[dict]:
    host = host or Host()
    results = []
    for g in REGISTRY.values():
        if g.when != when:
            continue
        try:
            status, detail = g.check(host)
        except Exception as error:  # a guard that cannot check is a failed guard
            status, detail = "fail", f"{type(error).__name__}: {error}"
        results.append({"id": g.id, "status": status, "detail": detail})
    return results


def failed(results: list[dict]) -> bool:
    return any(r["status"] == "fail" for r in results)


@guard("G-vram-sysfs", mistakes=("M1",))
def vram_sysfs(host: Host):
    files = sorted(host.drm.glob("card*/device/mem_info_vram_used"))
    if len(files) != 1:
        return "fail", f"expected exactly one mem_info_vram_used, found {[str(f) for f in files]}"
    return "ok", str(files[0])


@guard("G-runtime-pm", mistakes=("M15",))
def runtime_pm(host: Host):
    files = sorted(host.drm.glob("card*/device/mem_info_vram_used"))
    if len(files) != 1:
        return "fail", "no single GPU to check"
    control = (files[0].parent / "power" / "control").read_text().strip()
    if control != "on":
        return "fail", f"power/control is {control!r}; runtime PM can evict the model (want 'on')"
    return "ok", "power/control = on"


@guard("G-unit-path", mistakes=("M2",))
def unit_path(host: Host):
    missing = [tool for tool in ("llama-yield", "bwrap", "git", "cmake", "systemd-run", "python3")
               if not shutil.which(tool, path=host.unit_path)]
    if missing:
        return "fail", f"not on the unit PATH: {missing}"
    python = shutil.which("python3", path=host.unit_path)
    probe = subprocess.run([python, "-c", "import PIL, tomllib"], capture_output=True, text=True)
    if probe.returncode:
        return "fail", f"{python} on the unit PATH lacks Pillow or tomllib"
    return "ok", f"tools resolve on {host.unit_path}; python3 = {python}"


@guard("G-disk", mistakes=("M9",))
def disk(host: Host):
    limits = host.config
    eval_free = shutil.disk_usage(host.eval_root).free >> 30
    root_free = shutil.disk_usage(host.system_root).free >> 30
    problems = []
    if os.stat(host.eval_root).st_dev == os.stat(host.system_root).st_dev:
        problems.append(f"{host.eval_root} is on the root filesystem")
    if eval_free < limits["min_eval_free_gib"]:
        problems.append(f"{host.eval_root} has {eval_free} GiB free")
    if root_free < limits["min_root_free_gib"]:
        problems.append(f"/ has {root_free} GiB free")
    return ("fail", "; ".join(problems)) if problems else ("ok", f"eval {eval_free} GiB, / {root_free} GiB free")


@guard("G-kernel-pending", mistakes=("M54",))
def kernel_pending(host: Host):
    """A kernel installed but not booted splits a long run across kernels at the next reboot."""
    default = host.boot / "vmlinuz"
    if not default.is_symlink():
        return "skip", f"{default} is not a symlink to a versioned kernel"
    installed = default.resolve().name.removeprefix("vmlinuz-")
    if installed != host.kernel:
        return "fail", (f"kernel {installed} is installed but {host.kernel} is running: a reboot mid-run "
                        "would measure arms on different kernels; reboot first")
    return "ok", f"running the default kernel {host.kernel}"


@guard("G-memory", mistakes=("M17",))
def memory(host: Host):
    info = dict(line.split(":", 1) for line in host.meminfo.read_text().splitlines() if ":" in line)
    available = int(info["MemAvailable"].split()[0]) >> 20
    fstype = _fstype(host.mounts, host.eval_root)
    problems = []
    if available < host.config["min_mem_available_gib"]:
        problems.append(f"MemAvailable {available} GiB")
    if fstype == "tmpfs":
        problems.append(f"{host.eval_root} is on tmpfs (rows would cost RAM and vanish on reboot)")
    return ("fail", "; ".join(problems)) if problems else ("ok", f"MemAvailable {available} GiB, eval on {fstype}")


def _fstype(mounts: Path, path: Path) -> str:
    best, fstype = "", "unknown"
    target = str(Path(path).resolve())
    for line in mounts.read_text().splitlines():
        parts = line.split()
        mount = parts[1].replace("\\040", " ")
        if (target == mount or target.startswith(mount.rstrip("/") + "/")) and len(mount) > len(best):
            best, fstype = mount, parts[2]
    return fstype




@guard("G-models-readable", mistakes=("M18", "M49"))
def models_readable(host: Host):
    """Every model path the run's serve candidates mount (production's without a plan) is readable."""
    candidates = (host.plan or {}).get("candidates", {}).values()
    specs = [c["spec"] for c in candidates if c.get("kind") == "serve"]
    if host.plan is None:
        specs = [incumbent()["spec"]]
    bad = set()
    for spec in specs:
        paths = [Path(value) for value in spec["mounts"].values()]
        for value in spec["args"]:
            for inside, outside in spec["mounts"].items():
                if value == inside or value.startswith(inside.rstrip("/") + "/"):
                    paths.append(Path(outside) / value[len(inside):].lstrip("/"))
        bad |= {str(path) for path in paths if not os.access(path, os.R_OK)}
    if bad:
        return "fail", f"unreadable spec model paths: {sorted(bad)}"
    return "ok", f"model paths of {len(specs)} serve spec(s) readable"


@guard("G-engine-age", mistakes=("M12",))
def engine_age(host: Host):
    """Compare the exported production image with the most recent radiance release."""
    try:
        from .build import latest_radiance_release
        production = incumbent()
        sidecar = json.loads((Path(production["spec"]["rootfs"]) / ".nous-serve-image.json").read_text())
        latest = latest_radiance_release()
    except Exception as exc:
        return "warn", f"cannot check radiance release age: {exc}"
    image_ref = sidecar.get("image", "")
    exported_at = sidecar.get("exported_at", "")
    age_days = (time.time() - datetime.fromisoformat(exported_at.replace("Z", "+00:00")).timestamp()) / 86400
    if image_ref != latest["image_ref"]:
        return "warn", f"production image {image_ref} is behind latest {latest['image_ref']} (exported {age_days:.0f} days ago)"
    return "ok", f"production image {image_ref} is latest (exported {age_days:.0f} days ago)"


@guard("G-sandbox", mistakes=("M21", "M24"))
def sandbox(host: Host):
    """The grader's sandbox runs code, confined, as the current user would (with its process count)."""
    probe = ("import pathlib, socket\n"
             "for attempt in (lambda: pathlib.Path(%r, '.nevl-probe').write_text('x'),\n"
             "                lambda: socket.create_connection(('1.1.1.1', 53), timeout=3)):\n"
             "    try:\n        attempt()\n        print('ESCAPED')\n    except OSError:\n        pass\n"
             "print('confined')\n") % str(Path.home())
    rc, out, err, timed_out = run_python(probe, "", 20)
    if rc or timed_out or out.strip() != "confined":
        return "fail", f"sandbox probe rc={rc} timed_out={timed_out} out={out.strip()!r} err={err[-200:]!r}"
    return "ok", "graded code cannot write home or reach the network"






def _cpu_list(text: str) -> set[int]:
    """'8-11,14' -> {8, 9, 10, 11, 14}"""
    cpus = set()
    for part in text.strip().split(","):
        low, _, high = part.partition("-")
        cpus.update(range(int(low), int(high or low) + 1))
    return cpus


def _on_reserved_cpus(host: Host, pid: str) -> tuple[str, str]:
    """Is process `pid` in llama.slice and allowed exactly its CPUs?

    Reads the process's real affinity (/proc/PID/status): llama.slice does not
    delegate cpuset to its children, so a leaf cgroup has no cpuset files."""
    cgroup = (host.proc / pid / "cgroup").read_text().strip().split("::", 1)[1]
    if not cgroup.startswith("/llama.slice/"):
        return "fail", f"process {pid} is in {cgroup}, not llama.slice"
    status = (host.proc / pid / "status").read_text()
    allowed = _cpu_list(re.search(r"^Cpus_allowed_list:\s*(\S+)", status, re.M).group(1))
    reserved = _cpu_list((host.cgroup_root / "llama.slice" / "cpuset.cpus.effective").read_text())
    if allowed != reserved:
        return "fail", f"process {pid} may run on CPUs {sorted(allowed)}, llama.slice has {sorted(reserved)}"
    return "ok", f"{cgroup} on CPUs {sorted(allowed)}"


@guard("G-reserved-cpus", when="host", mistakes=("M28",))
def reserved_cpus(host: Host):
    """The lease check below, run on production now: the same code, the real cgroup layout."""
    pid = host.production_pid
    if pid is None:
        out = subprocess.run(["systemctl", "show", "-p", "MainPID", "--value", PRODUCTION_UNIT],
                             capture_output=True, text=True).stdout.strip()
        pid = int(out or 0)
    if not pid:
        return "warn", f"{PRODUCTION_UNIT} is not running; reserved CPUs unchecked"
    return _on_reserved_cpus(host, str(pid))


@guard("G-lease-cpuset", when="lease", mistakes=("M16", "M23"))
def lease_cpuset(host: Host):
    status, detail = _on_reserved_cpus(host, "self")
    if status == "ok" and LEASE_UNIT not in detail:
        return "fail", f"not in the lease unit: {detail}"
    return status, detail


@guard("G-load", when="lease", mistakes=("M16",))
def load(host: Host):
    one_minute = float(host.loadavg.read_text().split()[0])
    if one_minute > host.config["max_loadavg"]:
        return "warn", f"load average {one_minute} during the lease: timings may be noisy"
    return "ok", f"load average {one_minute}"


@guard("G-vram-free", when="lease", mistakes=("M29",))
def vram_free(host: Host):
    """The GPU is empty before the first server. The driver frees a stopped
    process's VRAM over several seconds, so wait for it (ledger M29)."""
    used_file = sorted(host.drm.glob("card*/device/mem_info_vram_used"))[0]
    deadline = time.monotonic() + host.config.get("vram_settle_s", 60)
    while True:
        used = int(used_file.read_text()) >> 20
        if used <= host.config["max_idle_vram_mib"]:
            return "ok", f"{used} MiB VRAM in use"
        if time.monotonic() >= deadline:
            return "fail", f"{used} MiB VRAM still in use: something else holds the GPU"
        time.sleep(1)


def production_health(timeout_s: int = 300) -> tuple[bool, str]:
    """After a lease: production must be active and its model must answer (llama-yield
    restores it). A model list alone is not enough: the router lists models it never
    loaded, e.g. when a leftover container still holds VRAM (council O-11)."""
    deadline = time.monotonic() + timeout_s
    model = incumbent()["model"]
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "ok"}],
                       "max_tokens": 1}).encode()
    state = "unknown"
    while time.monotonic() < deadline:
        state = subprocess.run(["systemctl", "is-active", PRODUCTION_UNIT], capture_output=True,
                               text=True).stdout.strip()
        request = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", body,
                                          {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=max(5.0, deadline - time.monotonic())):
                pass
            if state == "active":
                return True, f"{PRODUCTION_UNIT} active; {model} answered"
        except OSError:
            pass
        time.sleep(5)
    return False, f"{PRODUCTION_UNIT} is {state} and {model} did not answer on :8080 within {timeout_s}s"

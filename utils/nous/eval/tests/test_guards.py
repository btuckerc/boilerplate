import os
import shutil
import subprocess
import time

import pytest

from nevl import guards
from nevl.guards import Host

CONFIG = {"min_eval_free_gib": 0, "min_root_free_gib": 0, "min_mem_available_gib": 1, "max_loadavg": 4.0,
          "max_idle_vram_mib": 2048}


def host(tmp_path, **kwargs):
    return Host(**{"config": CONFIG, "eval_root": tmp_path, **kwargs})


def gpu(tmp_path, cards=("card1",), control="on", vram=512 << 20):
    drm = tmp_path / "drm"
    for card in cards:
        device = drm / card / "device"
        (device / "power").mkdir(parents=True)
        (device / "mem_info_vram_used").write_text(str(vram))
        (device / "power" / "control").write_text(control)
    return drm


def test_vram_sysfs_needs_exactly_one_card(tmp_path):
    assert guards.vram_sysfs(host(tmp_path, drm=gpu(tmp_path)))[0] == "ok"
    assert guards.vram_sysfs(host(tmp_path, drm=gpu(tmp_path / "two", ("card0", "card1"))))[0] == "fail"


def test_runtime_pm_requires_on(tmp_path):
    assert guards.runtime_pm(host(tmp_path, drm=gpu(tmp_path, control="auto")))[0] == "fail"
    assert guards.runtime_pm(host(tmp_path, drm=gpu(tmp_path / "on")))[0] == "ok"


def test_vram_free_waits_for_the_driver_to_release_production(tmp_path):
    import threading

    config = {**CONFIG, "vram_settle_s": 3}
    drm = gpu(tmp_path, vram=6 << 30)
    used = drm / "card1" / "device" / "mem_info_vram_used"
    threading.Timer(0.5, used.write_text, [str(57 << 20)]).start()  # production's VRAM drains
    assert guards.vram_free(host(tmp_path, drm=drm, config=config))[0] == "ok"
    used.write_text(str(20 << 30))  # something else keeps the GPU
    assert guards.vram_free(host(tmp_path, drm=drm, config=config))[0] == "fail"


def test_unit_path_reports_missing_tools(tmp_path):
    status, detail = guards.unit_path(host(tmp_path, unit_path=str(tmp_path)))
    assert status == "fail" and "llama-yield" in detail


def test_disk_rejects_the_root_filesystem(tmp_path):
    status, detail = guards.disk(host(tmp_path, system_root=tmp_path))
    assert status == "fail" and "root filesystem" in detail


def test_memory_rejects_tmpfs(tmp_path):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 134217728 kB\nMemAvailable: 67108864 kB\n")
    mounts = tmp_path / "mounts"
    mounts.write_text(f"/dev/a / ext4 rw 0 0\ntmpfs {tmp_path} tmpfs rw 0 0\n")
    status, detail = guards.memory(host(tmp_path, meminfo=meminfo, mounts=mounts))
    assert status == "fail" and "tmpfs" in detail
    mounts.write_text("/dev/a / ext4 rw 0 0\n")
    assert guards.memory(host(tmp_path, meminfo=meminfo, mounts=mounts))[0] == "ok"


def test_models_readable_checks_serve_spec_mounts(tmp_path, monkeypatch):
    model = tmp_path / "model"
    model.mkdir()
    monkeypatch.setattr(guards, "incumbent", lambda: {"spec": {
        "mounts": {"/models": str(tmp_path)}, "args": ["--model", "/models/model"]}})
    assert guards.models_readable(host(tmp_path))[0] == "ok"
    monkeypatch.setattr(guards, "incumbent", lambda: {"spec": {
        "mounts": {"/models": str(tmp_path)}, "args": ["--model", "/models/missing"]}})
    assert guards.models_readable(host(tmp_path))[0] == "fail"


def _engine_host(tmp_path, monkeypatch, image):
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir(exist_ok=True)
    (rootfs / ".nous-serve-image.json").write_text(
        '{"image": "%s", "exported_at": "2026-11-01T00:00:00+00:00"}' % image)
    monkeypatch.setattr(guards, "incumbent", lambda: {"spec": {"rootfs": str(rootfs)}})
    monkeypatch.setattr("nevl.build.latest_radiance_release",
                        lambda: {"image_ref": "ghcr.io/slybase/vllm-sly-radiance:2.0.0-rocm10.1"})
    return host(tmp_path)


def test_engine_age_warns_when_production_lags(tmp_path, monkeypatch):
    status, detail = guards.engine_age(_engine_host(tmp_path, monkeypatch,
        "ghcr.io/slybase/vllm-sly-radiance:1.9.1-rocm10.1"))
    assert status == "warn" and "behind latest" in detail


def test_engine_age_reports_latest_image(tmp_path, monkeypatch):
    status, detail = guards.engine_age(_engine_host(tmp_path, monkeypatch,
        "ghcr.io/slybase/vllm-sly-radiance:2.0.0-rocm10.1"))
    assert status == "ok" and "is latest" in detail




def cgroup_tree(tmp_path, pid, cgroup, allowed, slice_cpus="8-11"):
    """A fake /sys/fs/cgroup and /proc/PID shaped like nous: cpuset files only on llama.slice."""
    root = tmp_path / "cgroup"
    (root / "llama.slice").mkdir(parents=True, exist_ok=True)
    (root / "llama.slice" / "cpuset.cpus.effective").write_text(slice_cpus + "\n")
    proc = tmp_path / "proc" / pid
    proc.mkdir(parents=True)
    (proc / "cgroup").write_text(f"0::{cgroup}\n")
    (proc / "status").write_text(f"Name:\tpython3\nCpus_allowed:\tf00\nCpus_allowed_list:\t{allowed}\n")
    return root, tmp_path / "proc"


def test_lease_cpuset_checks_the_process_affinity(tmp_path):
    root, proc = cgroup_tree(tmp_path, "self", "/llama.slice/llama-yield-gpu.service", "8-11")
    assert guards.lease_cpuset(host(tmp_path, cgroup_root=root, proc=proc))[0] == "ok"
    root, proc = cgroup_tree(tmp_path / "sys", "self", "/system.slice/llama-yield-gpu.service", "0-7,12-31")
    status, detail = guards.lease_cpuset(host(tmp_path, cgroup_root=root, proc=proc))
    assert status == "fail" and "system.slice" in detail
    root, proc = cgroup_tree(tmp_path / "wide", "self", "/llama.slice/llama-yield-gpu.service", "0-31")
    assert guards.lease_cpuset(host(tmp_path, cgroup_root=root, proc=proc))[0] == "fail"


def test_reserved_cpus_probe_reads_this_hosts_real_layout():
    """The lease guard's code on the live production process (ledger M28): a fixture
    tree only encodes what we believed the cgroup layout to be."""
    if subprocess.run(["systemctl", "is-active", "--quiet", "llama.service"]).returncode:
        pytest.skip("llama.service is not running here")
    status, detail = guards.reserved_cpus(Host(config=CONFIG))
    assert status == "ok", detail


def test_load_warns_when_busy(tmp_path):
    loadavg = tmp_path / "loadavg"
    loadavg.write_text("9.5 3 2 1/100 1\n")
    assert guards.load(host(tmp_path, loadavg=loadavg))[0] == "warn"


def test_a_guard_that_crashes_counts_as_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(guards, "REGISTRY", {"G-x": guards.Guard("G-x", "host", (), lambda h: 1 / 0)})
    assert guards.failed(guards.run("host", host(tmp_path)))

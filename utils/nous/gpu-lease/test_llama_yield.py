"""llama-yield: no output holds up a lease's stop, production's restore or the lease lock (ledger M62);
no start goes into a lost GPU or beside stuck processes, and an outage shows (ledger M84)."""
import importlib.machinery
import importlib.util
import os
import threading
import time
from pathlib import Path

import pytest

loader = importlib.machinery.SourceFileLoader("llama_yield", str(Path(__file__).resolve().parent / "llama-yield"))
spec = importlib.util.spec_from_loader(loader.name, loader)
llama_yield = importlib.util.module_from_spec(spec)
loader.exec_module(llama_yield)


@pytest.fixture(autouse=True)
def no_host(tmp_path, monkeypatch):
    """No test reads the host's GPU or cgroups or writes its /run."""
    monkeypatch.setattr(llama_yield, "SYSFS", tmp_path / "no-sysfs")
    monkeypatch.setattr(llama_yield, "CGROUP_ROOT", tmp_path / "no-cgroup")
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path / "no-run")
    monkeypatch.setattr(llama_yield, "LOCK", str(tmp_path / "llama-yield.lock"))


@pytest.fixture
def stalled():
    """The write end of a full pipe whose reader never reads: a write to it blocks."""
    reader, writer = os.pipe2(os.O_NONBLOCK)
    try:
        while True:
            os.write(writer, b"x" * 4096)
    except BlockingIOError:
        pass
    os.set_blocking(writer, True)
    yield writer
    os.close(reader)  # a writer still blocked on it gets EPIPE and ends
    os.close(writer)


def returns_within(seconds, call):
    """Run call in a daemon thread; a call that blocks fails the test instead of hanging it."""
    worker = threading.Thread(target=call, daemon=True)
    worker.start()
    worker.join(timeout=seconds)
    return not worker.is_alive()


def test_systemd_runs_output_never_waits_for_a_caller_that_stopped_reading(stalled):
    """systemd-run blocked writing its report never exited, and llama-yield waits for it before
    releasing the lease lock (release audits)."""
    source, sink = os.pipe()
    relay = llama_yield.Relay(source, stalled)
    # 16 MiB: far more than the pipe and the relay's queue hold
    assert returns_within(20, lambda: [os.write(sink, b"y" * 4096) for _ in range(4000)])
    os.close(sink)
    assert returns_within(3, relay.finish)


@pytest.mark.parametrize("stall", ["syslog", "stdout"])
def test_an_announcement_waits_for_a_stalled_output_at_most_a_second(stalled, monkeypatch, stall):
    """recover() announces before it starts production; a stalled log kept production down."""
    if stall == "syslog":  # never released: the daemon thread it blocks ends with the process
        monkeypatch.setattr(llama_yield.syslog, "syslog", lambda *args: time.sleep(3600))
    else:
        monkeypatch.setattr(llama_yield.syslog, "syslog", lambda *args: None)
    saved = os.dup(1)
    os.dup2(stalled, 1)
    try:
        returned = returns_within(2, lambda: llama_yield.announce("llama-watchdog: starting llama.service"))
    finally:
        os.dup2(saved, 1)
        os.close(saved)
    assert returned


def make_gpu(tmp_path, config=b"\x02\x10"):
    sysfs = tmp_path / "sys"
    bdf = "0000:03:00.0"
    bound = sysfs / "bus/pci/drivers/amdgpu" / bdf
    bound.parent.mkdir(parents=True)
    target = sysfs / "devices/pci0000:00/0000:00:01.0/0000:01:00.0/0000:02:00.0" / bdf
    target.mkdir(parents=True)
    (target / "config").write_bytes(config)
    bound.symlink_to(target)
    llama_yield.SYSFS = sysfs  # restored by no_host's monkeypatch
    device = sysfs / "bus/pci/devices" / bdf
    device.parent.mkdir(parents=True, exist_ok=True)
    device.symlink_to(target)
    return sysfs, bdf


@pytest.mark.parametrize(("config", "lost"), [(b"\xff\xff", True), (b"x", True), (b"\x02\x10", False)])
def test_gpu_lost_reads_config(tmp_path, config, lost):
    make_gpu(tmp_path, config)
    assert bool(llama_yield.gpu_lost()) is lost


def test_gpu_lost_when_no_device_or_config(tmp_path):
    sysfs, bdf = make_gpu(tmp_path)
    (sysfs / "bus/pci/drivers/amdgpu" / bdf).unlink()
    assert "no amdgpu" in llama_yield.gpu_lost()
    bound = sysfs / "bus/pci/drivers/amdgpu" / bdf
    (sysfs / "bus/pci/devices" / bdf).unlink()
    target = sysfs / "bus/pci/devices" / bdf
    target.mkdir(parents=True)
    bound.symlink_to(target)
    assert bdf in llama_yield.gpu_lost()


def test_leftovers_walks_cgroup_and_excludes_self(tmp_path, monkeypatch):
    root = tmp_path / "cg"
    (root / "unit/child").mkdir(parents=True)
    (root / "unit/cgroup.procs").write_text(f"{os.getpid()}\n41\n")
    (root / "unit/child/cgroup.procs").write_text("42\n")
    monkeypatch.setattr(llama_yield, "CGROUP_ROOT", root)
    monkeypatch.setattr(llama_yield, "ctl", lambda *args: "/unit")
    assert llama_yield.leftovers("llama.service") == [41, 42]


def test_condition_exits_for_lost_and_leftovers(monkeypatch):
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: "GPU lost; reboot")
    assert llama_yield.production_condition() == 1
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: None)
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: [42])
    assert llama_yield.production_condition() == 1
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: [])
    assert llama_yield.production_condition() == 0
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: 1 / 0)
    assert llama_yield.production_condition() == 0  # a broken check must not keep production down


def test_lost_gpu_refuses_lease_before_production_control(monkeypatch, capsys):
    monkeypatch.setattr(llama_yield.sys, "argv", ["llama-yield", "--", "echo", "test"])
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: "GPU lost; reboot")
    calls = []
    monkeypatch.setattr(llama_yield, "systemctl", lambda *args: calls.append(args))
    with pytest.raises(SystemExit) as error:
        llama_yield.main()
    assert error.value.code == 2
    assert "refusing lease" in capsys.readouterr().err
    assert calls == []


@pytest.mark.parametrize(("lost", "pids"), [("lost", []), (None, [7])])
def test_watchdog_skips_lost_gpu_or_leftovers(monkeypatch, tmp_path, lost, pids):
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path)
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: lost)
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: pids)
    monkeypatch.setattr(llama_yield, "properties", lambda unit: {
        "ActiveState": "failed", "UnitFileState": "enabled",
        "InactiveEnterTimestampMonotonic": "0"})
    monkeypatch.setattr(llama_yield, "leases", lambda: [])
    starts = []
    monkeypatch.setattr(llama_yield, "ctl", lambda *args: starts.append(args))
    args = type("Args", (), {"assume_llama_disabled": False, "assume_bonsai_active": False,
                              "restore": False, "dry_run": False})()
    llama_yield.recover(args)
    assert not any("start" in call for call in starts)


@pytest.mark.parametrize("broken", ["marker", "telemetry"])
def test_a_failing_marker_or_telemetry_never_stops_the_restart(monkeypatch, tmp_path, broken):
    """Reporting is best effort: a full or read-only /run, or a sysfs read that raises, is logged
    and the pass still restores a healthy production (ledger M84)."""
    def fail(*args):
        raise OSError(28, "No space left on device")
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path)
    monkeypatch.setattr(llama_yield, "down_marker" if broken == "marker" else "telemetry", fail)
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: None)
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: [])
    monkeypatch.setattr(llama_yield, "properties", lambda unit: {
        "ActiveState": "failed", "UnitFileState": "enabled",
        "InactiveEnterTimestampMonotonic": "0"})
    monkeypatch.setattr(llama_yield, "leases", lambda: [])
    said = []
    monkeypatch.setattr(llama_yield, "announce", said.append)
    starts = []
    monkeypatch.setattr(llama_yield, "ctl", lambda *args: starts.append(args))
    args = type("Args", (), {"assume_llama_disabled": False, "assume_bonsai_active": False,
                              "restore": False, "dry_run": False})()
    assert llama_yield.recover(args) == 0
    assert ("--no-block", "start", "llama.service") in starts
    assert any(f"llama-watchdog: {broken}: " in line and "No space left" in line for line in said)


def test_watchdog_dry_run_does_not_create_marker_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path / "run")
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: "lost")
    monkeypatch.setattr(llama_yield, "properties", lambda unit: {
        "ActiveState": "failed", "UnitFileState": "enabled",
        "InactiveEnterTimestampMonotonic": "0"})
    monkeypatch.setattr(llama_yield, "leases", lambda: [])
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: [])
    monkeypatch.setattr(llama_yield, "announce", lambda message: None)
    args = type("Args", (), {"assume_llama_disabled": False, "assume_bonsai_active": False,
                              "restore": False, "dry_run": True})()
    llama_yield.recover(args)
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize(("active", "leased", "lost", "age", "marker"), [
    (False, False, False, 0, False), (False, False, False, 601, True),
    (True, False, False, 601, False), (False, True, False, 601, False),
    (False, False, True, 0, True), (False, True, True, 0, True), (True, False, True, 0, True),
])
def test_down_marker_lifecycle(tmp_path, monkeypatch, active, leased, lost, age, marker):
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path)
    monkeypatch.setattr(llama_yield.time, "time", lambda: 1000)
    if active or leased:
        (tmp_path / "down-since").write_text("1")
        (tmp_path / "production-down").write_text("stale")
    elif age:
        (tmp_path / "down-since").write_text(str(1000 - age))
    args = type("Args", (), {"dry_run": False})()
    llama_yield.down_marker(args, active, leased, lost, "down")
    assert (tmp_path / "production-down").exists() is marker


@pytest.mark.parametrize("content", ["", "garbage", "nan", "inf", "5000", "-1e100", "0", "1e300"])
def test_a_broken_down_since_is_repaired_so_the_alert_still_fires(tmp_path, monkeypatch, content):
    """An interrupted first write leaves down-since empty; every pass used to restart the clock
    without repairing it, so production-down never appeared (audit 20261108T070748-audit-e2f1)."""
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path)
    (tmp_path / "down-since").write_text(content)
    now = [1000.0]
    monkeypatch.setattr(llama_yield.time, "time", lambda: now[0])
    args = type("Args", (), {"dry_run": False})()
    llama_yield.down_marker(args, False, False, False, "down")
    assert float((tmp_path / "down-since").read_text()) == 1000.0
    assert not (tmp_path / "production-down").exists()
    assert not (tmp_path / ".down-since.tmp").exists()
    now[0] = 1601.0
    llama_yield.down_marker(args, False, False, False, "down")
    assert (tmp_path / "production-down").exists()


def test_down_marker_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path / "missing")
    args = type("Args", (), {"dry_run": True})()
    llama_yield.down_marker(args, False, False, True, "lost")
    assert not (tmp_path / "missing").exists()
    assert "would write" in capsys.readouterr().out


def test_telemetry_missing_files_and_lost_avoid_hwmon(tmp_path, monkeypatch):
    sysfs, bdf = make_gpu(tmp_path)
    assert "edge=?" in llama_yield.telemetry()
    (sysfs / "bus/pci/devices" / bdf / "config").write_bytes(b"\xff\xff")
    monkeypatch.setattr(llama_yield, "telemetry", lambda: (_ for _ in ()).throw(AssertionError("telemetry read while lost")))
    monkeypatch.setattr(llama_yield, "properties", lambda unit: {
        "ActiveState": "failed", "UnitFileState": "enabled", "InactiveEnterTimestampMonotonic": "0"})
    monkeypatch.setattr(llama_yield, "leases", lambda: [])
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: [])
    monkeypatch.setattr(llama_yield, "announce", lambda message: None)
    llama_yield.recover(type("Args", (), {"assume_llama_disabled": False, "assume_bonsai_active": False,
                                           "restore": False, "dry_run": True})())


@pytest.mark.parametrize("lost", [None, "GPU 0000:03:00.0 is lost"])
def test_a_watchdog_pass_during_a_lease_logs_telemetry_and_flags_a_lost_gpu(tmp_path, monkeypatch, lost):
    """The GPU fails under a lease's load: a watchdog pass that skips for the lease still logs
    telemetry and raises the outage marker for a lost GPU, even when the placeholder fails
    (release audits NousGpuGuard, NousGpuGuardB)."""
    said = []
    monkeypatch.setattr(llama_yield.sys, "argv", ["llama-yield", "--watchdog"])
    monkeypatch.setattr(llama_yield.os, "geteuid", lambda: 0)
    monkeypatch.setattr(llama_yield, "RUN_DIR", tmp_path)
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: lost)
    monkeypatch.setattr(llama_yield, "telemetry", lambda: "GPU telemetry: edge=60C")
    monkeypatch.setattr(llama_yield, "announce", said.append)

    def masked(args):
        raise llama_yield.subprocess.CalledProcessError(1, ["systemctl", "start", "llama-placeholder.service"])
    monkeypatch.setattr(llama_yield, "reconcile_placeholder", masked)
    monkeypatch.setattr(llama_yield, "recover", lambda args: pytest.fail("recovered under a lease"))
    with open(llama_yield.LOCK, "w") as lease:
        llama_yield.fcntl.flock(lease, llama_yield.fcntl.LOCK_EX)
        assert llama_yield.main() == 0
    assert ("GPU telemetry: edge=60C" in said) is (lost is None)
    assert (tmp_path / "production-down").exists() is (lost is not None)


def test_release_refuses_healthy(monkeypatch):
    monkeypatch.setattr(llama_yield.os, "geteuid", lambda: 0)
    monkeypatch.setattr(llama_yield, "gpu_lost", lambda: None)
    with pytest.raises(OSError, match="healthy"):
        llama_yield.release_gpu(type("Args", (), {"dry_run": False})())


def test_release_gpu_remove_then_rescan(tmp_path, monkeypatch):
    sysfs, bdf = make_gpu(tmp_path, b"\xff\xff")
    (sysfs / "bus/pci/devices").mkdir(parents=True, exist_ok=True)
    top = sysfs / "bus/pci/devices/0000:01:00.0"
    top.mkdir()
    (top / "remove").write_text("")
    (sysfs / "bus/pci/rescan").parent.mkdir(parents=True, exist_ok=True)
    (sysfs / "bus/pci/rescan").write_text("")
    monkeypatch.setattr(llama_yield.os, "geteuid", lambda: 0)
    monkeypatch.setattr(llama_yield, "leftovers", lambda unit: [])
    monkeypatch.setattr(llama_yield.time, "sleep", lambda _: None)
    writes = []
    original = Path.write_text
    def record(path, content, *args, **kwargs):
        if path.name in {"remove", "rescan"}:
            writes.append(path.name)
        return original(path, content, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", record)
    assert llama_yield.release_gpu(type("Args", (), {"dry_run": False})()) == 0
    assert writes == ["remove", "rescan"]

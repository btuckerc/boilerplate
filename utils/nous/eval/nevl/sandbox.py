from __future__ import annotations

import os
import subprocess
import tempfile


def _uid_process_count() -> int:
    uid = os.getuid()
    count = 0
    for entry in os.scandir("/proc"):
        if not entry.name.isdecimal():
            continue
        try:
            with open(os.path.join(entry.path, "status"), encoding="ascii") as f:
                status = f.read()
            real_uid = int(next(line.split()[1] for line in status.splitlines() if line.startswith("Uid:")))
            if real_uid == uid:
                count += len(os.listdir(os.path.join(entry.path, "task")))
        except (OSError, StopIteration, ValueError):
            continue
    return count


def run_python(source: str, stdin: str, timeout_s: float, mem_mb: int = 2048):
    """Run untrusted Python in a networkless bubblewrap namespace."""
    with tempfile.TemporaryDirectory(prefix="nevl-") as td:
        program = os.path.join(td, "solution.py")
        with open(program, "w", encoding="utf-8") as f:
            f.write(source)
        nproc = _uid_process_count() + 16
        cpu = max(1, int(timeout_s) + 1)
        wrapper = (
            "import os, resource, sys; "
            f"resource.setrlimit(resource.RLIMIT_AS, ({mem_mb * 1024 * 1024}, {mem_mb * 1024 * 1024})); "
            f"resource.setrlimit(resource.RLIMIT_CPU, ({cpu}, {cpu})); "
            f"resource.setrlimit(resource.RLIMIT_NPROC, ({nproc}, {nproc})); "
            f"resource.setrlimit(resource.RLIMIT_FSIZE, ({64 * 1024 * 1024}, {64 * 1024 * 1024})); "
            "os.execv(sys.executable, [sys.executable, '/solution.py'])"
        )
        command = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
                   "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
                   "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                   "--ro-bind", program, "/solution.py"]
        for path in ("/lib64", "/bin", "/etc/alternatives"):
            if os.path.exists(path):
                command[1:1] = ["--ro-bind", path, path]
        command += ["--", "/usr/bin/python3", "-c", wrapper]
        try:
            p = subprocess.run(command, input=stdin, text=True, capture_output=True, timeout=timeout_s)
            return p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            return -1, e.stdout or "", e.stderr or "", True

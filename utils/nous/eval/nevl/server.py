"""Start and stop one candidate's server on the benchmark port."""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .candidate import process_env
from .ctx import Context


class ServerError(RuntimeError):
    pass


class Server:
    def __init__(self, candidate: dict, run_dir: Path, port: int):
        self.candidate = candidate
        self.run_dir = Path(run_dir)
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.log_path = self.run_dir / "logs" / f"{candidate['label']}.server.log"
        if candidate["kind"] == "command":
            self.base_url = candidate["base_url"].rstrip("/")
        else:
            self.base_url = f"http://127.0.0.1:{port}"
        self.listen_port = urllib.parse.urlsplit(self.base_url).port

    def argv(self) -> list[str]:
        c = self.candidate
        if c["kind"] == "command":
            return c["start"]
        if c["kind"] == "serve":
            spec_path = self.run_dir / "specs" / f"{c['label']}.json"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(json.dumps(c["spec"], indent=2) + "\n")
            return ["/usr/local/bin/nous-serve", "run", str(spec_path), "--port", str(self.port)]
        preset = self.run_dir / "presets" / f"{c['label']}.ini"
        preset.parent.mkdir(parents=True, exist_ok=True)
        preset.write_text(c["preset_text"])
        return [c["engine"], "--models-preset", str(preset), "--models-max", "1", "--models-autoload",
                "--host", "127.0.0.1", "--port", str(self.port), *c["args"]]
    def start(self) -> float:
        """Launch, wait for the model to answer one request; return seconds from spawn."""
        if _port_open(self.listen_port):
            raise ServerError(f"port {self.listen_port} is already in use; refusing to measure a stranger")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        with self.log_path.open("ab") as log:
            self.proc = subprocess.Popen(self.argv(), env=process_env(self.candidate), stdout=log,
                                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                         start_new_session=True)
        deadline = started + self.candidate["ready_timeout_s"]
        try:
            self._wait_listed(deadline)
            self._probe(timeout=max(1.0, deadline - time.monotonic()))
        except BaseException:
            self.stop()
            raise
        return time.monotonic() - started

    def check_alive(self) -> None:
        """Raise if the server died or stopped answering during a block.

        A crashed engine fails every later item in milliseconds; the block must
        name the crash and its log, not leave a pile of row errors (ledger M42)."""
        if self.proc is not None and self.proc.poll() is not None:
            raise ServerError(f"server exited with {self.proc.returncode} during the block; see {self.log_path}")
        try:
            self._probe(timeout=60)
        except Exception as error:
            raise ServerError(f"server stopped answering during the block ({error}); "
                              f"see {self.log_path}") from error

    def _probe(self, timeout: float) -> None:
        Context(self.base_url, self.candidate["model"], request=self.candidate["request"]).chat(
            {"messages": [{"role": "user", "content": "Reply with OK."}], "max_tokens": 4,
             "reasoning_effort": "low"}, timeout=timeout)

    def _wait_listed(self, deadline: float) -> None:
        model = self.candidate["model"]
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise ServerError(f"server exited with {self.proc.returncode}; see {self.log_path}")
            try:
                with urllib.request.urlopen(self.base_url + "/v1/models", timeout=5) as response:
                    if any(m.get("id") == model for m in json.load(response).get("data", [])):
                        return
            except OSError:
                pass
            time.sleep(1)
        raise ServerError(f"{model} not listed within the ready timeout; see {self.log_path}")

    def stop(self) -> None:
        if self.proc is None:
            return
        if self.candidate["kind"] == "command" and self.candidate["stop"]:
            subprocess.run(self.candidate["stop"], env=process_env(self.candidate),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        for sig, wait in ((signal.SIGTERM, 60), (signal.SIGKILL, 30)):
            try:
                os.killpg(self.proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                self.proc.wait(timeout=wait)
                break
            except subprocess.TimeoutExpired:
                continue
        self.proc = None
        deadline = time.monotonic() + 30
        while _port_open(self.listen_port) and time.monotonic() < deadline:
            time.sleep(0.5)

    def kill(self) -> None:
        """Fast stop for a lease teardown; the server stays in the lease cgroup."""
        if self.proc is not None:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def vram_mib(drm: Path = Path("/sys/class/drm")) -> int:
    """Used VRAM of the one discrete GPU (ledger M1: never a hard-coded card number)."""
    files = sorted(drm.glob("card*/device/mem_info_vram_used"))
    if len(files) != 1:
        raise RuntimeError(f"expected one mem_info_vram_used, found {len(files)}")
    return int(files[0].read_text()) >> 20

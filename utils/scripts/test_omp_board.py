#!/usr/bin/env python3
"""omp-board is harness-neutral: a Claude Code or OMP director ancestor owns locks and leases."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / "home/dot_local/bin/executable_omp-board"


@pytest.mark.parametrize("harness", ["claude", "omp"])
def test_owner_is_the_nearest_director_ancestor(tmp_path, harness):
    # A shell script named like the harness: the kernel names the process after the script,
    # so `ps -o comm=` reports it as the director. It prints its own pid after the board's answer.
    director = tmp_path / harness
    director.write_text(f"#!/bin/sh\n{sys.executable} {BOARD} owner\necho \"$$\"\n")
    director.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "OMP_BOARD_OWNER"}
    out = subprocess.run([str(director)], env=env, capture_output=True, text=True, timeout=30, check=True).stdout.split()
    assert out[0] == f"host={os.uname().nodename}"
    assert out[1] == f"pid={out[2]}"


def test_owner_override_and_selftest(tmp_path):
    env = dict(os.environ, OMP_BOARD_OWNER="4242")
    out = subprocess.run([sys.executable, str(BOARD), "owner"], env=env, capture_output=True, text=True, check=True).stdout
    assert out.strip().endswith("pid=4242")
    done = subprocess.run([sys.executable, str(BOARD), "selftest"], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr

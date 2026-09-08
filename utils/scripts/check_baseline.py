#!/usr/bin/env python3
"""Offline source checks, also usable against an exported commit snapshot."""
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib


def check(root):
    bash = next((str(p) for p in (Path("/opt/homebrew/bin/bash"), Path("/usr/local/bin/bash"))
                 if p.is_file()), shutil.which("bash"))
    version = subprocess.check_output([bash, "-c", "printf '%s' \"$BASH_VERSION\""], text=True)
    assert int(version.split(".")[0]) >= 4, "Bash 4+ required; on macOS install the Brewfile's bash formula"
    home = root / "home"
    tools = tomllib.loads((home / "dot_config/mise/config.toml").read_text())["tools"]
    for tool in ("codex", "github:can1357/oh-my-pi"):
        assert re.fullmatch(r"\d+\.\d+\.\d+", tools[tool]), f"{tool}: exact release required"
    omp = tools["github:can1357/oh-my-pi"]
    manifest = (home / "dot_config/decent-angl/omp-baseline-manifest.tsv").read_text()
    assert re.search(r"^# omp-version\s+" + re.escape(omp) + r"$", manifest, re.M), "OMP manifest pin differs"
    setup = (home / "run_onchange_after_04-setup-omp.sh.tmpl").read_text()
    assert f"OMP_VERSION=\"{omp}\"" in setup, "OMP setup pin differs"

    count = 0
    for path in (home / "dot_local/bin").glob("executable_*"):
        if path.suffix == ".tmpl" or not path.is_file():
            continue
        text = path.read_text()
        first = text.partition("\n")[0]
        if "python" in first:
            ast.parse(text, filename=str(path))
        elif first in ("#!/usr/bin/env bash", "#!/bin/bash", "#!/bin/sh", "#!/usr/bin/env sh"):
            shell = bash if "bash" in first else "sh"
            subprocess.run([shell, "-n", str(path)], check=True)
        else:
            continue
        count += 1
    fleet = home / "dot_config/decent-angl/fleet.json"
    if fleet.exists():
        hosts = json.loads(fleet.read_text())["hosts"]
        assert len({h["id"] for h in hosts}) == len(hosts), "Duplicate fleet host id"
        for host in hosts:
            assert re.fullmatch(r"[a-z][a-z0-9-]*", host["id"]), "Invalid host id"
            assert re.fullmatch(r"(?:[a-z_][a-z0-9_-]*@)?[a-z0-9.-]+", host["ssh"]), "Invalid SSH target"
    print(f"BASELINE pins and {count} executable syntax checks passed")


if __name__ == "__main__":
    check(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])

#!/usr/bin/env python3
"""Per-file overlay apply and 3-way merge for omarchy-shell-overlay."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "home" / "dot_local" / "bin" / "executable_omarchy-shell-overlay"
SHELL_QML = (
    'readonly property string firstPartyPluginsDir: shellPath + "/plugins"\n'
    "QtObject {}\n"
)
FILLER = "\n".join(f"  // filler {i}" for i in range(80)) + "\n"
WS = "plugins/bar/widgets/Workspaces.qml"
NET = "plugins/panels/network/Panel.qml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def hashed(packaged: Path, *rels: str) -> str:
    lines = [f"{sha256(packaged / rel)}  {rel}" for rel in rels]
    return "\n".join(lines) + "\n"


def tree() -> tuple[Path, dict[str, str]]:
    root = Path(tempfile.mkdtemp(prefix="omarchy-overlay-"))
    omarchy = root / "omarchy"
    overlay = root / "overlay"
    state = root / "state"
    (omarchy / "shell").mkdir(parents=True)
    overlay.mkdir()
    state.mkdir()
    write(omarchy / "shell" / "shell.qml", SHELL_QML)
    env = os.environ.copy()
    env["XDG_STATE_HOME"] = str(state)
    env["OMARCHY_PATH"] = str(omarchy)
    env["OMARCHY_SHELL_OVERLAY_DIR"] = str(overlay)
    env["OMARCHY_SHELL_OVERLAY_BASE"] = str(state / "decent-angl" / "omarchy-shell-overlay-base")
    return root, env


def run(env: dict[str, str], *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


def runtime(env: dict[str, str], rel: str) -> Path:
    return Path(env["XDG_STATE_HOME"]) / "decent-angl" / "omarchy-shell-runtime" / "shell" / rel


def packaged(env: dict[str, str], rel: str) -> Path:
    return Path(env["OMARCHY_PATH"]) / "shell" / rel


def overlay(env: dict[str, str], rel: str) -> Path:
    return Path(env["OMARCHY_SHELL_OVERLAY_DIR"]) / rel


def base(env: dict[str, str], rel: str) -> Path:
    return Path(env["OMARCHY_SHELL_OVERLAY_BASE"]) / rel


def seed_match(env: dict[str, str]) -> None:
    write(packaged(env, WS), 'text: "1"\n')
    write(packaged(env, NET), 'text: "wifi"\n')
    write(overlay(env, WS), 'text: "\\u25CF"\n')
    write(overlay(env, NET), 'text: "Connected"\n')
    write(Path(env["OMARCHY_SHELL_OVERLAY_DIR"]) / "upstream.sha256", hashed(Path(env["OMARCHY_PATH"]) / "shell", WS, NET))


def test_match_copies_overlay_and_snapshots_base() -> None:
    root, env = tree()
    try:
        seed_match(env)
        proc = run(env, "sync-runtime")
        assert proc.returncode == 0, proc.stderr
        assert runtime(env, WS).read_text(encoding="utf-8") == 'text: "\\u25CF"\n'
        assert runtime(env, NET).read_text(encoding="utf-8") == 'text: "Connected"\n'
        assert "Quickshell.shellDir" in runtime(env, "shell.qml").read_text(encoding="utf-8")
        assert base(env, WS).read_text(encoding="utf-8") == 'text: "1"\n'
        status = run(env, "status").stdout
        assert "NEXT    overlay" in status
        assert "UPSTREAM match" in status
        assert f"MATCH   {WS}" in status
    finally:
        subprocess.run(["rm", "-rf", str(root)], check=False)


def test_one_drifted_file_does_not_drop_the_rest() -> None:
    root, env = tree()
    try:
        seed_match(env)
        run(env, "sync-runtime")
        write(packaged(env, NET), 'text: "ethernet"\n')
        # Drop the network base so this path cannot merge.
        base(env, NET).unlink()
        proc = run(env, "sync-runtime")
        assert proc.returncode == 0, proc.stderr
        assert runtime(env, WS).read_text(encoding="utf-8") == 'text: "\\u25CF"\n'
        assert runtime(env, NET).read_text(encoding="utf-8") == 'text: "ethernet"\n'
        status = run(env, "status").stdout
        assert "NEXT    overlay" in status
        assert f"MATCH   {WS}" in status
        assert f"SKIP    {NET} no-base" in status
        drift = (Path(env["XDG_STATE_HOME"]) / "decent-angl" / "omarchy-shell-overlay.drift").read_text(encoding="utf-8")
        assert f"SKIP {NET} no-base" in drift
    finally:
        subprocess.run(["rm", "-rf", str(root)], check=False)


def test_merge_keeps_overlay_edits_and_new_packaged_api() -> None:
    root, env = tree()
    try:
        header = "Panel {\n  id: root\n"
        phrases = '  property string connectionPhrase: "Wiring bits"\n'
        api_old = "  function connectKnown(ssid) { network.connect() }\n"
        api_new = "  function connectDirectly(ssid) { network.connect() }\n"
        footer_old = '  Text { text: root.connectionPhrase }\n}\n'
        footer_ours = '  Text { text: "Connected" }\n}\n'
        old_pkg = header + phrases + FILLER + api_old + FILLER + footer_old
        ours = header + FILLER + api_old + FILLER + footer_ours
        new_pkg = header + phrases + FILLER + api_new + FILLER + footer_old
        write(packaged(env, WS), 'text: "1"\n')
        write(packaged(env, NET), old_pkg)
        write(overlay(env, WS), 'text: "\\u25CF"\n')
        write(overlay(env, NET), ours)
        write(Path(env["OMARCHY_SHELL_OVERLAY_DIR"]) / "upstream.sha256", hashed(Path(env["OMARCHY_PATH"]) / "shell", WS, NET))
        run(env, "sync-runtime")
        write(packaged(env, NET), new_pkg)
        proc = run(env, "sync-runtime")
        assert proc.returncode == 0, proc.stderr
        merged = runtime(env, NET).read_text(encoding="utf-8")
        assert 'text: "Connected"' in merged
        assert "connectDirectly" in merged
        assert "Wiring bits" not in merged
        assert "connectKnown" not in merged
        assert runtime(env, WS).read_text(encoding="utf-8") == 'text: "\\u25CF"\n'
        # Overlay source is unchanged; merge is runtime-only.
        assert overlay(env, NET).read_text(encoding="utf-8") == ours
        status = run(env, "status").stdout
        assert f"MERGE   {NET}" in status
        assert "NEXT    overlay" in status
    finally:
        subprocess.run(["rm", "-rf", str(root)], check=False)


def test_conflict_uses_packaged_for_that_path() -> None:
    root, env = tree()
    try:
        write(packaged(env, WS), 'text: "1"\n')
        write(packaged(env, NET), "foo\n")
        write(overlay(env, WS), 'text: "\\u25CF"\n')
        write(overlay(env, NET), "bar\n")
        write(Path(env["OMARCHY_SHELL_OVERLAY_DIR"]) / "upstream.sha256", hashed(Path(env["OMARCHY_PATH"]) / "shell", WS, NET))
        run(env, "sync-runtime")
        write(packaged(env, NET), "baz\n")
        proc = run(env, "sync-runtime")
        assert proc.returncode == 0, proc.stderr
        assert runtime(env, NET).read_text(encoding="utf-8") == "baz\n"
        assert runtime(env, WS).read_text(encoding="utf-8") == 'text: "\\u25CF"\n'
        status = run(env, "status").stdout
        assert f"SKIP    {NET} conflict" in status
        assert "NEXT    overlay" in status
    finally:
        subprocess.run(["rm", "-rf", str(root)], check=False)


def main() -> int:
    test_match_copies_overlay_and_snapshots_base()
    test_one_drifted_file_does_not_drop_the_rest()
    test_merge_keeps_overlay_edits_and_new_packaged_api()
    test_conflict_uses_packaged_for_that_path()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

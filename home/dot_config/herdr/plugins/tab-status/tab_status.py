"""Mirror each Herdr tab's agent state into its label: "2" -> "2 ◐".

Runs on every relevant Herdr event and reconciles all tabs on this server, so
a missed or reordered event is corrected by the next one. Glyphs match the
sidebar's `status_indicators = "symbols"` set.
"""

import fcntl
import json
import os
import re
import subprocess

GLYPHS = {"blocked": "×", "working": "◐", "done": "✓", "idle": "○"}
SUFFIX = re.compile(r" [" + "".join(GLYPHS.values()) + r"]$")
HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")


def herdr(*args):
    return subprocess.run(
        [HERDR, *args], check=True, capture_output=True, text=True
    ).stdout


def desired_label(tab):
    base = SUFFIX.sub("", tab["label"])
    # Numeric labels track the tab's position so closing or moving tabs
    # renumbers them; any other text is a manual name and is kept.
    if base.isdigit():
        base = str(tab["number"])
    glyph = GLYPHS.get(tab.get("agent_status"))
    return f"{base} {glyph}" if glyph else base


def main():
    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR", "/tmp")
    os.makedirs(state_dir, exist_ok=True)
    # Serialize runs: a slower run must not overwrite a newer state.
    with open(os.path.join(state_dir, "reconcile.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        tabs = json.loads(herdr("tab", "list"))["result"]["tabs"]
        for tab in tabs:
            label = desired_label(tab)
            if label != tab["label"]:
                herdr("tab", "rename", tab["tab_id"], label)


if __name__ == "__main__":
    main()

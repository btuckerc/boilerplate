#!/usr/bin/env python3
"""Check the drawn workspace marks and opacity bindings in the overlay widget."""

from __future__ import annotations

import re
from pathlib import Path


QML = Path(__file__).parents[2] / "home" / "dot_local" / "share" / "omarchy-shell-overlay" / "plugins" / "bar" / "widgets" / "Workspaces.qml"


def uncomment(source: str) -> str:
    return re.sub(r"//[^\n]*", "", source)


def main() -> int:
    source = uncomment(QML.read_text(encoding="utf-8"))
    assert "\\u25C" not in source, "workspace marks are drawn, not dot glyphs (font metrics put glyphs off centre)"
    assert re.search(r"\btext\s*:\s*\"\"", source), "the button carries no text"
    assert re.search(r"\blabelVisible\s*:\s*false", source), "the label stays hidden"
    assert re.search(r"\bhasVisualContent\s*:\s*true", source), "an empty text must not hide the button"
    assert "Rectangle {" in source, "each workspace draws a Rectangle mark"
    assert re.search(r"property real active:\s*shown \? 1 : 0", source), "the mark morphs between square (0) and bar (1)"
    assert re.search(r"Behavior on active", source) and re.search(r"Behavior on opacity", source), "length and opacity animate"
    assert "2 * Math.round((8 + 8 * active) * dpr / 2) / dpr" in source, "length snaps to an even number of device pixels"
    assert "antialiasing: false" in source, "edges stay hard on whole pixels"
    assert "pressScale" not in source, "no scale transform on the mark (it would break pixel alignment)"
    assert "model: root.ids" in source, "marks build from the stable list so they animate rather than rebuild"
    assert "modeProc" not in source, "the unused layout-mode reader is gone"
    assert re.search(r"fixedWidth:\s*root.vertical \? root.barSize : 24", source), "24-px slots"

    opacity_binding = re.search(r"\bopacity\s*:\s*(.+)", source)
    assert opacity_binding, "opacity binding is missing"
    opacity = opacity_binding.group(1)
    assert "shown ? 1" in opacity, "shown opacity must be 1"
    assert "occupied ? 0.55 : 0.3" in opacity, "occupied must read stronger (0.55) than empty (0.3)"
    tooltip = re.search(r"\btooltipText\s*:\s*(.+)", source)
    assert tooltip and "slot" in tooltip.group(1), "workspace number must move to the tooltip"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    mark = re.search(r"Rectangle\s*\{(.*?)\n\s*\}", source, re.S)
    assert mark, "each workspace draws a Rectangle mark"
    body = mark.group(1)
    assert "anchors.centerIn: parent" in body, "the mark is centred by geometry"
    assert re.search(r"width:\s*shown && !root.vertical \? 16 : 8", body), "shown is a 16-px bar, others 8"
    assert re.search(r"height:\s*shown && root.vertical \? 16 : 8", body), "marks are 8 px thick"
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

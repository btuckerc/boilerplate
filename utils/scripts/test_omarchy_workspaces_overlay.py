#!/usr/bin/env python3
"""Check the workspace mark and opacity bindings in the overlay widget."""

from __future__ import annotations

import re
from pathlib import Path


QML = Path(__file__).parents[2] / "home" / "dot_local" / "share" / "omarchy-shell-overlay" / "plugins" / "bar" / "widgets" / "Workspaces.qml"


def uncomment(source: str) -> str:
    return re.sub(r"//[^\n]*", "", source)


def main() -> int:
    source = uncomment(QML.read_text(encoding="utf-8"))
    text_binding = re.search(r"\btext\s*:\s*(.+)", source)
    assert text_binding and "shown" in text_binding.group(1), "text binding must include shown (the monitor's active workspace)"
    assert "\\u25CF" in text_binding.group(1), "text binding must use U+25CF for filled marks"
    assert "\\u25CB" in text_binding.group(1), "text binding must use U+25CB for empty marks"

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

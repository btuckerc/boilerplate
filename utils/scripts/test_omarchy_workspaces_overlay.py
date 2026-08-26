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
    assert text_binding and "focused" in text_binding.group(1), "text binding must include focused"
    assert "\\u25CF" in text_binding.group(1), "text binding must use U+25CF for filled marks"
    assert "\\u25CB" in text_binding.group(1), "text binding must use U+25CB for empty marks"

    opacity_binding = re.search(r"\bopacity\s*:\s*(.+)", source)
    assert opacity_binding, "opacity binding is missing"
    opacity = opacity_binding.group(1)
    assert "focused ? 1" in opacity, "focused opacity must be 1"
    assert "occupied ? 0.45" in opacity, "occupied-unfocused opacity must be 0.45"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

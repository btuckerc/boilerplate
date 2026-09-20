"""Sanitized 12-case fixture used for the local Laya trials."""
CASES = [
    ("extract", "Read the supplied 30-row CSV and return the five rows with status failed. No web access or inference required.", "local"),
    ("format", "Convert palette.json to palette.csv preserving exact row order and numeric values. Only output format changes.", "local"),
    ("overflow", "Fix the indexed4 row byte calculation for odd widths and SIZE_MAX without integer overflow, then compile and run the existing tests.", "luna"),
    ("rename", "Rename a TypeScript function across 12 files, update imports and run the test suite.", "luna"),
    ("ui", "Change the CSS button padding from 8px to 12px and verify the page.", "luna"),
    ("architecture", "Design the asynchronous DMA buffer ownership and cancellation protocol for an ESP32 renderer sharing PSRAM with an emulator. Timing is inconsistent and the cause is unknown.", "astra"),
    ("diagnosis", "Three attempted fixes still produce rare corrupted video frames; logs contradict the presumed ownership model. Diagnose root cause across interrupts and DMA callbacks.", "astra"),
    ("research", "Critically compare agent execution policies using primary research and reconcile conflicting evidence before choosing the architecture.", "astra"),
    ("continue", "Continue.", "retain"),
    ("steer", "Actually use Luna for this task.", "luna"),
    ("override", "Keep this entirely local. Summarize the supplied 1KB build log.", "local"),
    ("ambiguous", "Make it better.", "retain"),
]
CRITERIA = {
    "local": "Bounded mechanical file transform or extraction using supplied text, one file, cheap exact verification. Local 9B model is weak at algorithmic reasoning, tools and large context; never use it for diagnosing unknown bugs or independent arithmetic design.",
    "luna": "Capable coding model for ordinary implementation, tests, navigation, routine computer use and bounded debugging. Default for clear implementable work. Can use tools and run tests.",
    "astra": "Frontier reasoning for ambiguous architecture, unexplained repeated failures, deep conflicting research or hard decisions. Higher cost; unnecessary for routine edits.",
    "retain": "Context-dependent continuation or unclear request that cannot be safely classified from the provided text. Preserve the current model; do not guess.",
}

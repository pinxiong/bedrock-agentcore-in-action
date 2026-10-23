#!/usr/bin/env python3
"""Unit checks for the streaming sanitizer in app/aia_uc04/model/sanitize.py.

The sanitizer is copied between use cases on purpose (series invariant I4), so
this file is the uc04 copy of the uc03 checks. The chunk lists are the shapes
measured against Bedrock on 2026-10-14, including the case that matters most:
the DeepSeek marker arrives split across deltas, so a filter that inspected
whole deltas would miss it. Reproduced live on 2026-10-23: the pre-sanitizer
invoke leaked `<｜DSML｜function_calls` into the reply (evidence/17-invoke-200.txt).

Run:  python tests/test_sanitize.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "aia_uc04"))

from model.sanitize import StreamSanitizer  # noqa: E402

CASES: list[tuple[str, list[str], str]] = [
    (
        "deepseek DSML marker split across deltas (measured)",
        ["Refunding now.\n\n<", "｜DSML｜", "function_c", "alls"],
        "Refunding now.\n\n",
    ),
    (
        "nova thinking block, open tag itself split",
        ["<think", "ing> check policy ", "</thinking>", "\nDone."],
        "\nDone.",
    ),
    (
        "the block after the DSML marker is dropped entirely",
        ["Sure. <", "｜DSML｜", "function_calls", "｜invoke name=processRefund｜"],
        "Sure. ",
    ),
    (
        "ascii DSML variant, in case a gateway rewrites the bar",
        ["Hello <|DSML|>function_calls"],
        "Hello ",
    ),
    (
        "plain text passes through unchanged",
        ["The refund id ", "is RF-123 ", "for SO-2214."],
        "The refund id is RF-123 for SO-2214.",
    ),
    (
        "a lone '<' in prose is held back then released, not eaten",
        ["amount 200 ", "< ", "500 so allowed"],
        "amount 200 < 500 so allowed",
    ),
]


def run() -> int:
    failures = 0
    for name, chunks, expected in CASES:
        s = StreamSanitizer()
        got = "".join(s.feed(c) for c in chunks) + s.flush()
        if got != expected:
            failures += 1
            print(f"FAIL {name}\n  got      {got!r}\n  expected {expected!r}")
        else:
            print(f"ok   {name}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())

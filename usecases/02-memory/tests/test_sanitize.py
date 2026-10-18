#!/usr/bin/env python3
"""Unit checks for the streaming sanitizer in app/aia_uc02/model/sanitize.py.

The chunk lists below are the shapes actually measured against Bedrock on
2026-10-14, including the case that matters most: the DeepSeek marker arrives
split across four deltas, so a filter that inspected whole deltas would miss it.

Run:  python tests/test_sanitize.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "aia_uc02"))

from model.sanitize import StreamSanitizer  # noqa: E402

CASES: list[tuple[str, list[str], str]] = [
    (
        "deepseek DSML marker split across four deltas (measured)",
        ["I'll use the calculator tool to add 17 and 25 for you.\n\n<", "｜DSML｜", "function_c", "alls"],
        "I'll use the calculator tool to add 17 and 25 for you.\n\n",
    ),
    (
        "nova thinking block, open tag itself split",
        ["<think", "ing> I need to use", " the tool ", "</thinking>", "\nThe sum is 42."],
        "\nThe sum is 42.",
    ),
    (
        "the block after the DSML marker is dropped entirely",
        ["Sure, let me check. <", "｜DSML｜", "function_calls", "｜invoke name=add_numbers｜"],
        "Sure, let me check. ",
    ),
    (
        "ascii DSML variant, in case a gateway rewrites the bar",
        ["Hello <|DSML|>function_calls"],
        "Hello ",
    ),
    (
        "plain text passes through unchanged",
        ["Just ", "a normal ", "answer."],
        "Just a normal answer.",
    ),
    (
        "a lone '<' in prose is held back then released, not eaten",
        ["is 3 ", "< ", "4?"],
        "is 3 < 4?",
    ),
]


def run_chunks(chunks: list[str]) -> str:
    scrub = StreamSanitizer()
    emitted = "".join(scrub.feed(chunk) for chunk in chunks)
    return emitted + scrub.flush()


def main() -> int:
    failed = 0
    for name, chunks, expected in CASES:
        got = run_chunks(chunks)
        ok = got == expected
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            failed += 1
            print(f"        expected {expected!r}")
            print(f"        got      {got!r}")
    print(f"\n{len(CASES) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

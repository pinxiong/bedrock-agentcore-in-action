"""Strip model scaffolding out of the streamed text channel.

Two leaks reproduce on Bedrock in us-east-1, measured on 2026-10-14 by calling
ConverseStream with boto3 alone, so neither one is a Strands bug:

  * ``deepseek.v3.2`` writes a truncated chat-template marker
    (``<｜DSML｜function_calls``) into the assistant text, then switches to a
    well-formed ``toolUse`` block. Everything from the marker on is scaffolding,
    so the remainder of that turn is dropped.
  * ``amazon.nova-*`` writes a balanced ``<thinking>...</thinking>`` block ahead
    of its answer. The block is dropped and the answer after it is kept.

Deltas arrive split at arbitrary boundaries: one delta can end with ``<`` while
the next begins with ``｜DSML｜``. A filter that inspected whole deltas would miss
the marker, so this one holds back a short suffix that could still grow into a
marker, and emits only text it can prove is clean.
"""

from __future__ import annotations

# The fullwidth vertical bar U+FF5C is what DeepSeek emits. The ASCII form is
# accepted too, because editors and gateways rewrite one into the other without
# asking.
_DSML_MARKERS = ("<｜DSML｜", "<|DSML|")
_THINK_OPEN = "<thinking>"
_THINK_CLOSE = "</thinking>"
_MARKERS = (*_DSML_MARKERS, _THINK_OPEN, _THINK_CLOSE)


def _suffix_prefix_len(text: str, markers: tuple[str, ...]) -> int:
    """Length of the longest suffix of text that could still become a marker."""
    longest = 0
    for marker in markers:
        for size in range(1, len(marker)):
            if text.endswith(marker[:size]):
                longest = max(longest, size)
    return longest


class StreamSanitizer:
    """Feed it text deltas, get back only the text that is safe to show."""

    def __init__(self) -> None:
        self._pending = ""
        self._in_thinking = False
        self._cut = False

    def feed(self, text: str) -> str:
        """Add one delta and return the clean text it completes."""
        if self._cut:
            return ""
        self._pending += text
        return self._drain(final=False)

    def flush(self) -> str:
        """Release any held-back text once the stream has ended."""
        if self._cut:
            return ""
        return self._drain(final=True)

    def _drain(self, final: bool) -> str:
        out: list[str] = []
        while self._pending:
            if self._in_thinking:
                close = self._pending.find(_THINK_CLOSE)
                if close == -1:
                    keep = _suffix_prefix_len(self._pending, (_THINK_CLOSE,))
                    self._pending = self._pending[-keep:] if keep else ""
                    return "".join(out)
                self._pending = self._pending[close + len(_THINK_CLOSE):]
                self._in_thinking = False
                continue

            hits = sorted((self._pending.find(m), m) for m in _MARKERS)
            hits = [(index, marker) for index, marker in hits if index != -1]
            if hits:
                index, marker = hits[0]
                out.append(self._pending[:index])
                if marker in _DSML_MARKERS:
                    self._cut = True
                    self._pending = ""
                    return "".join(out)
                self._pending = self._pending[index + len(marker):]
                self._in_thinking = True
                continue

            keep = _suffix_prefix_len(self._pending, _MARKERS)
            if final or not keep:
                out.append(self._pending)
                self._pending = ""
            else:
                out.append(self._pending[: len(self._pending) - keep])
                self._pending = self._pending[len(self._pending) - keep:]
            break
        return "".join(out)

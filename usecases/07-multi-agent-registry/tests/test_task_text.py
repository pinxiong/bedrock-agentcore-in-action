#!/usr/bin/env python3
"""Unit checks for the A2A task text extraction in app/aia_uc07/a2a_client.py.

The task shapes below mirror what StrandsA2AExecutor actually returns: the
agent's final answer lands in artifacts, the status message is set on
completion, and history carries the intermediate turns (which may include
model scaffolding that must not be preferred over the final answer).

Run:  python -m pytest tests/test_task_text.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "aia_uc07"))

from a2a_client import task_text  # noqa: E402


def _part(text: str) -> dict:
    return {"kind": "text", "text": text}


def test_status_message_wins() -> None:
    task = {
        "status": {"state": "completed", "message": {"parts": [_part("final answer")]}},
        "history": [{"role": "agent", "parts": [_part("intermediate scaffolding")]}],
    }
    assert task_text(task) == "final answer"


def test_artifacts_when_no_status_message() -> None:
    task = {
        "status": {"state": "completed"},
        "artifacts": [{"name": "agent_response", "parts": [_part("from artifacts")]}],
        "history": [{"role": "agent", "parts": [_part("intermediate")]}],
    }
    assert task_text(task) == "from artifacts"


def test_history_is_last_resort_and_agent_only() -> None:
    task = {
        "status": {"state": "working"},
        "history": [
            {"role": "user", "parts": [_part("the question")]},
            {"role": "agent", "parts": [_part("partial thought")]},
        ],
    }
    assert task_text(task) == "partial thought"


def test_empty_task() -> None:
    assert task_text({}) == ""

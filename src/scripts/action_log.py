"""Append-only JSON-lines log of review decisions
(default: data/review_actions.jsonl).

Same design as the script log (src/scripts/log.py):
  - One JSON object per line. Lines are only ever added, never edited.
  - A line only counts once it ends with a newline. The newline is written
    last, so a crash mid-write leaves a partial tail that readers skip and the
    next save cuts off.

One decision per script id, and the first one recorded wins:
  - Saving an identical decision again (same outcome, reviewer and text) adds
    nothing and returns False.
  - Saving any other decision for that script raises AlreadyDecidedError.

If a save fails, append() raises ActionSaveError. It never returns True unless
the line is on disk.

This log stores decisions; it does not judge them. Whether a script may be
approved at all is decided first, by decide() in src/scripts/actions.py.

Like the other logs, it supports one writer at a time. data/ is in .gitignore.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from src.scripts.actions import Decision, InvalidReviewerError, ReviewAction, check_repeat

DEFAULT_ACTION_LOG_PATH = Path("data") / "review_actions.jsonl"


class ActionSaveError(Exception):
    """A review decision could not be saved to the log."""


def _to_entry(action: ReviewAction) -> dict:
    return {
        "script_id": action.script_id,
        "decision": action.decision.value,
        "reviewer": action.reviewer,
        "note": action.note,
        "content_hash": action.content_hash,
        "decided_at": action.decided_at.isoformat(),
    }


def _to_action(entry: dict) -> ReviewAction:
    return ReviewAction(
        script_id=entry["script_id"],
        decision=Decision(entry["decision"]),
        reviewer=entry["reviewer"],
        note=entry["note"],
        content_hash=entry["content_hash"],
        decided_at=datetime.fromisoformat(entry["decided_at"]),
    )


class ActionLog:
    def __init__(self, path=DEFAULT_ACTION_LOG_PATH):
        self.path = Path(path)

    def append(self, action: ReviewAction) -> bool:
        """Record the decision.

        Returns True if a line was added, False if this identical decision was
        already recorded. Raises AlreadyDecidedError if the script already has
        a different one, InvalidReviewerError if the reviewer name is blank,
        and ActionSaveError if it could not be saved.
        """
        if not action.reviewer:
            raise InvalidReviewerError("A reviewer name is required")
        try:
            existing = self.get(action.script_id)
            if existing is not None:
                check_repeat(existing, action.decision, action.reviewer, action.content_hash)
                return False
            self._write(_to_entry(action))
        except (OSError, ValueError) as err:  # ValueError: corrupt log, see read()
            raise ActionSaveError(
                f"Could not save the decision on {action.script_id!r} "
                f"to {self.path}: {err}") from err
        return True

    def get(self, script_id: str):
        """The decision recorded for this script, or None if there is none.
        Raises (never returns None) if the log cannot be read."""
        for action in self.read():
            if action.script_id == script_id:
                return action  # the first one wins
        return None

    def read(self) -> list:
        """All complete decisions, oldest first. A half-written last line is
        skipped. A broken line anywhere else raises ValueError."""
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        complete = data[: data.rfind(b"\n") + 1]  # everything up to the last newline
        actions = []
        for number, raw in enumerate(complete.splitlines(), start=1):
            try:
                actions.append(_to_action(json.loads(raw.decode("utf-8"))))
            except (ValueError, KeyError, TypeError, AttributeError) as err:
                raise ValueError(f"{self.path}: line {number} is corrupt: {err!r}") from err
        return actions

    def _write(self, entry: dict) -> None:
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        with open(self.path, "r+b") as f:
            data = f.read()
            if data and not data.endswith(b"\n"):  # cut off an unfinished last line
                f.truncate(data.rfind(b"\n") + 1)
            f.seek(0, os.SEEK_END)
            f.write(line.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())

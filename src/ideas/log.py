"""Append-only JSON-lines log of ideas (default: data/ideas.jsonl).

- One JSON object per line. Lines are only ever added, never edited.
- A line only counts once it ends with a newline. The newline is written
  last, so a crash mid-write leaves a partial tail that readers skip.
- Each line has an idempotency key (idea id + status). Logging the same idea
  in the same status twice adds nothing. A status change (e.g. PENDING ->
  REMOVED) is a new key, so it appends a new line and history is kept.
- Only id, title, theme and status are written. Nothing else is logged.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.ideas.model import Idea

DEFAULT_LOG_PATH = Path("data") / "ideas.jsonl"


def idempotency_key(idea: Idea) -> str:
    return f"{idea.id}:{idea.status.value}"


class IdeaLog:
    def __init__(self, path=DEFAULT_LOG_PATH):
        self.path = Path(path)

    def append(self, idea: Idea, now=None) -> bool:
        """Log the idea. Returns True if a line was added, False if this
        exact idea+status was already logged."""
        key = idempotency_key(idea)
        if key in {entry["key"] for entry in self.read()}:
            return False

        entry = {
            "key": key,
            "logged_at": (now or datetime.now(timezone.utc)).isoformat(),
            "idea": {
                "id": idea.id,
                "title": idea.title,
                "theme": idea.theme,
                "status": idea.status.value,
            },
        }
        line = json.dumps(entry, ensure_ascii=False) + "\n"

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        with open(self.path, "r+b") as f:
            self._drop_partial_tail(f)
            f.seek(0, os.SEEK_END)
            f.write(line.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        return True

    def read(self) -> list:
        """Return all complete entries. A half-written last line is skipped.
        A broken line anywhere else raises, because that is real corruption."""
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        complete = data[: data.rfind(b"\n") + 1]  # everything up to the last newline
        entries = []
        for number, raw in enumerate(complete.splitlines(), start=1):
            try:
                entries.append(json.loads(raw.decode("utf-8")))
            except ValueError as err:  # includes UnicodeDecodeError
                raise ValueError(f"{self.path}: line {number} is corrupt: {err}") from err
        return entries

    @staticmethod
    def _drop_partial_tail(f) -> None:
        """If the file does not end in a newline, cut off the unfinished
        last line so the next record starts cleanly."""
        data = f.read()
        if data and not data.endswith(b"\n"):
            f.truncate(data.rfind(b"\n") + 1)

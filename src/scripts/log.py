"""Append-only JSON-lines log of scripts (default: data/scripts.jsonl).

Same design as the idea log (src/ideas/log.py), kept separate on purpose:
  - One JSON object per line. Lines are only ever added, never edited.
  - A line only counts once it ends with a newline. The newline is written
    last, so a crash mid-write leaves a partial tail that readers skip.
  - Each line has an idempotency key (script id + status). Logging the same
    script in the same status twice adds nothing. A status change (for
    example DRAFT -> FLAGGED) is a new key, so it appends a new line and the
    history is kept.
  - The full script text is logged, because a reviewer needs to read it,
    together with the reasons it was flagged (empty if it was not).

If a save fails for ANY reason, append() raises ScriptSaveError. It never
returns normally unless the line is on disk, so a script is never treated as
saved when it is not.

data/ is in .gitignore: scripts are working data and must not be committed.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.scripts.model import Script

DEFAULT_LOG_PATH = Path("data") / "scripts.jsonl"


class ScriptSaveError(Exception):
    """A script could not be saved to the log."""


def idempotency_key(script: Script) -> str:
    return f"{script.id}:{script.status.value}"


class ScriptLog:
    def __init__(self, path=DEFAULT_LOG_PATH):
        self.path = Path(path)

    def append(self, script: Script, reasons=(), now=None) -> bool:
        """Log the script with the flag reasons (FlagReason objects, if any).

        Returns True if a line was added, False if this exact script+status
        was already logged. Raises ScriptSaveError if it could not be saved.
        """
        try:
            return self._append(script, reasons, now)
        except (OSError, ValueError) as err:  # ValueError: corrupt log, see read()
            raise ScriptSaveError(
                f"Could not save script {script.id!r} to {self.path}: {err}") from err

    def _append(self, script, reasons, now) -> bool:
        key = idempotency_key(script)
        if key in {entry["key"] for entry in self.read()}:
            return False

        entry = {
            "key": key,
            "logged_at": (now or datetime.now(timezone.utc)).isoformat(),
            "script": {
                "id": script.id,
                "idea_id": script.idea_id,
                "title": script.title,
                "theme": script.theme,
                "intro": script.intro,
                "sections": list(script.sections),
                "conclusion": script.conclusion,
                "status": script.status.value,
            },
            "reasons": [
                {"code": reason.code.value, "detail": reason.detail} for reason in reasons
            ],
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

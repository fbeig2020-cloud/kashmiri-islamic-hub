"""Review actions: what a human reviewer decides about a flagged script.

This module is the model and the rules only. It reads and writes no files;
src/scripts/action_log.py saves the decisions.

Allowed changes:
    flagged -> approved   (not if the script has missing parts)
    flagged -> rejected
Approved and rejected are both FINAL. A script that is not flagged cannot be
reviewed. A script with missing parts can only be rejected. Every other flag
reason (blocked word, possible verse or hadith, pre-approved, ...) leaves the
choice to the reviewer.

Repeating a decision (same script text, same decision, same reviewer) records
nothing new, and the note from the first time is kept. Any other second
decision is refused.

Approving does not publish anything.

KNOWN LIMITS:
  - The reviewer is a typed-in name. There is no login, so the name proves
    nothing about who decided.
  - One reviewer at a time. Two people deciding at the same moment are not
    protected against each other.
  - Decisions are tied to the script id. A rejected script cannot be replaced
    by a regenerated one with the same id: the new text can never be approved.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from src.scripts.model import Script, ScriptStatus
from src.scripts.review import FlagCode


class Decision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ReviewAction:
    script_id: str
    decision: Decision
    reviewer: str
    content_hash: str  # fingerprint of the exact text the reviewer decided on
    decided_at: datetime
    note: str = ""

    def __post_init__(self):
        # Trimmed here so " Aisha " and "Aisha" are the same person everywhere.
        object.__setattr__(self, "reviewer", self.reviewer.strip())


class ReviewActionError(Exception):
    """A review decision was refused. Nothing should be recorded."""


class UnknownScriptError(ReviewActionError):
    pass


class InvalidReviewerError(ReviewActionError):
    pass


class NotFlaggedError(ReviewActionError):
    pass


class IncompleteScriptError(ReviewActionError):
    pass


class AlreadyDecidedError(ReviewActionError):
    pass


def content_hash(script: Script) -> str:
    """Fingerprint of what the reviewer reads. The status is left out, so only
    a change of text changes the hash."""
    parts = [script.title, script.theme, script.intro, list(script.sections), script.conclusion]
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode("utf-8")).hexdigest()


def check_repeat(existing: ReviewAction, decision: Decision, reviewer: str, text_hash: str):
    """For a script that already has a decision. Returns quietly if the new one
    is identical (same decision, reviewer and text); otherwise raises
    AlreadyDecidedError saying who decided what."""
    if (existing.decision, existing.reviewer, existing.content_hash) == (
            decision, reviewer.strip(), text_hash):
        return
    changed = "" if existing.content_hash == text_hash else " (on different text)"
    raise AlreadyDecidedError(
        f"Script {existing.script_id!r} was already {existing.decision.value} "
        f"by {existing.reviewer!r}{changed}; decisions are final")


def decide(
    script_id: str,
    script,
    reason_codes,
    decision: Decision,
    reviewer: str,
    existing=None,
    note: str = "",
    now=None,
):
    """Apply the rules to one reviewer decision.

    script_id     the id the reviewer asked for
    script        the flagged Script with that id, or None if there is none
    reason_codes  why it was flagged (FlagCode values or their strings)
    existing      the ReviewAction already recorded for this id, or None

    Returns the new ReviewAction to record, or None if this exact decision is
    already recorded. Raises a ReviewActionError if it is not allowed, and
    ValueError if `decision` is not approved or rejected.
    """
    decision = Decision(decision)

    if script is None:
        raise UnknownScriptError(f"There is no script with id {script_id!r}")
    if script.id != script_id:
        raise ValueError(f"Asked about {script_id!r} but was given script {script.id!r}")
    if existing is not None and existing.script_id != script_id:
        raise ValueError(
            f"Asked about {script_id!r} but was given a decision for {existing.script_id!r}")

    reviewer = (reviewer or "").strip()
    if not reviewer:
        raise InvalidReviewerError("A reviewer name is required")

    text_hash = content_hash(script)

    if existing is not None:
        check_repeat(existing, decision, reviewer, text_hash)
        return None

    if script.status != ScriptStatus.FLAGGED:
        raise NotFlaggedError(
            f"Script {script_id!r} is {script.status.value}, not flagged; "
            "only flagged scripts are reviewed")

    # Check the script itself too, in case the stored reasons are incomplete.
    incomplete = FlagCode.MISSING_PARTS in reason_codes or not script.is_complete
    if decision == Decision.APPROVED and incomplete:
        raise IncompleteScriptError(
            f"Script {script_id!r} has missing parts; it can only be rejected")

    return ReviewAction(
        script_id=script_id,
        decision=decision,
        reviewer=reviewer,
        content_hash=text_hash,
        decided_at=now or datetime.now(timezone.utc),
        note=note.strip(),
    )

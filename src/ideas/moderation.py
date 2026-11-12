"""Moderation: decide what happens to a generated idea.

Rules (see moderation_rules.json for the lists themselves):
  - Blocklist is checked first. Any hit -> BLOCKED.
  - Otherwise the idea is ALLOWED only if its theme is on the allowlist.
  - Everything else -> NEEDS_REVIEW (a human decides).

This module never approves or publishes anything. ALLOWED only means "nothing
stopped it"; the idea still waits as PENDING for a human.
"""

import json
import re
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from src.ideas.model import Idea, IdeaStatus

DEFAULT_RULES_PATH = Path(__file__).with_name("moderation_rules.json")


class Verdict(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class ModerationResult:
    verdict: Verdict
    reason: str


@dataclass(frozen=True)
class Rules:
    allowed_themes: tuple
    blocked_terms: tuple


def load_rules(path=DEFAULT_RULES_PATH):
    """Read the lists from the JSON file. Raises if the file is missing or
    malformed - we never fall back to "allow everything"."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return Rules(
        allowed_themes=tuple(t.strip().lower() for t in data["allowed_themes"]),
        blocked_terms=tuple(t.strip().lower() for t in data["blocked_terms"]),
    )


def _blocked_term_in(text, terms):
    # A term matches at the START of a word, so "kill" catches "killing"
    # but not "skill".
    for term in terms:
        if term and re.search(r"\b" + re.escape(term), text):
            return term
    return None


def moderate(idea, rules):
    text = f"{idea.title} {idea.theme}".lower()

    hit = _blocked_term_in(text, rules.blocked_terms)
    if hit:
        return ModerationResult(Verdict.BLOCKED, f"contains blocked term '{hit}'")

    if idea.theme.strip().lower() in rules.allowed_themes:
        return ModerationResult(Verdict.ALLOWED, "theme is on the allowlist")

    return ModerationResult(Verdict.NEEDS_REVIEW, "theme is not on the allowlist")


# Verdict -> status. APPROVED is deliberately absent: only a human sets it.
_STATUS_FOR_VERDICT = {
    Verdict.ALLOWED: IdeaStatus.PENDING,
    Verdict.BLOCKED: IdeaStatus.REMOVED,
    Verdict.NEEDS_REVIEW: IdeaStatus.FLAGGED,
}


def apply_moderation(idea, rules):
    """Moderate an idea and return (idea with its new status, the result).
    The original idea is not changed."""
    result = moderate(idea, rules)
    return replace(idea, status=_STATUS_FOR_VERDICT[result.verdict]), result

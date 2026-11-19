"""Review: decide whether a generated script must go to a human.

A script is FLAGGED, with a stored reason for each cause, when:
  - it has missing parts                      (MISSING_PARTS)
  - it hits the moderation blocklist          (BLOCKED_WORD)
  - its text may quote the Quran              (POSSIBLE_QURAN)
  - its text may quote a hadith               (POSSIBLE_HADITH)
  - its text has a long quotation             (POSSIBLE_QUOTATION)
  - its text contains Arabic script           (POSSIBLE_ARABIC)

A script with none of these stays DRAFT; it is NOT approved. Only a human
ever sets APPROVED, and nothing here drops a script.

Where each rule looks:
  - The blocklist (the same words STORY-001 uses, read from
    src/ideas/moderation_rules.json) is checked against the idea title, the
    idea theme, the script title and theme, and the script text.
  - The verse/hadith/quotation/Arabic patterns are checked against the
    script text only (intro, sections, conclusion).
All matching ignores upper/lower case.

KNOWN LIMITS (a human is still needed):
  - These are pattern matches, not understanding. A quote with no marker
    word gets through, and harmless uses of "verse" or "hadith" are flagged.
    Flagging too much is the safe error.
  - The citation pattern (number:number) also matches clock times like 10:30.
  - The Arabic-script rule flags ANY Arabic text, because we cannot tell a
    verse from a name or a dua. A smarter check is left for later.
  - Nothing here checks that a quotation is accurate.
"""

import re
from dataclasses import dataclass, replace
from enum import Enum

from src.ideas.model import Idea
from src.scripts.model import Script, ScriptStatus


class FlagCode(str, Enum):
    MISSING_PARTS = "missing_parts"
    BLOCKED_WORD = "blocked_word"
    POSSIBLE_QURAN = "possible_quran"
    POSSIBLE_HADITH = "possible_hadith"
    POSSIBLE_QUOTATION = "possible_quotation"
    POSSIBLE_ARABIC = "possible_arabic"
    PRE_APPROVED = "pre_approved"  # raised by the pipeline, not by review_script


@dataclass(frozen=True)
class FlagReason:
    code: FlagCode
    detail: str  # human-readable, e.g. "possible Quran verse: 'surah'"


@dataclass(frozen=True)
class ReviewResult:
    script: Script  # same script, with its new status
    reasons: tuple  # of FlagReason; empty means nothing was flagged

    @property
    def flagged(self) -> bool:
        return bool(self.reasons)


_FLAGS = re.IGNORECASE

_QURAN_PATTERNS = tuple(
    re.compile(p, _FLAGS)
    for p in (
        r"\b(?:surah|sura|ayah|ayat|verse)\b",
        r"\b\d{1,3}\s*:\s*\d{1,3}\b",  # a citation such as 2:255
        r"\ballah (?:says|said|tells us)\b",
    )
)

_HADITH_PATTERNS = tuple(
    re.compile(p, _FLAGS)
    for p in (
        r"\bhadith\b",
        r"\bnarrated\b",
        r"\breported by\b",
        # "sahih muslim", never a bare "muslim", so ordinary uses of the
        # word Muslim do not flag every script.
        r"\b(?:bukhari|sahih muslim|tirmidhi|abu dawud|nasa'?i|ibn majah)\b",
        r"\b(?:sahih|sunan)\b",
        r"\bthe prophet (?:\(?pbuh\)? )?said\b",
    )
)

_ARABIC = re.compile(r"[؀-ۿ]")
_QUOTED = re.compile(r'"([^"]*)"|“([^”]*)”')
_MIN_QUOTE_WORDS = 4


def _script_text(script: Script) -> str:
    return "\n".join([script.intro, *script.sections, script.conclusion])


def _first_match(patterns, text):
    for pattern in patterns:
        found = pattern.search(text)
        if found:
            return found.group(0)
    return None


def _long_quotation(text):
    for found in _QUOTED.finditer(text):
        quoted = found.group(1) if found.group(1) is not None else found.group(2)
        if len(quoted.split()) >= _MIN_QUOTE_WORDS:
            return quoted.strip()
    return None


def _blocked_term_in(text, terms):
    # Same rule as STORY-001: a term matches at the START of a word, so
    # "kill" catches "killing" but not "skill".
    for term in terms:
        if term and re.search(r"\b" + re.escape(term), text, _FLAGS):
            return term
    return None


def review_script(script: Script, idea: Idea, rules) -> ReviewResult:
    """Review one script. `rules` is what src.ideas.moderation.load_rules()
    returns. The original script is not changed."""
    reasons = []

    missing = script.missing_parts()
    if missing:
        reasons.append(FlagReason(
            FlagCode.MISSING_PARTS, f"missing parts: {', '.join(missing)}"))

    text = _script_text(script)

    everything = " ".join([idea.title, idea.theme, script.title, script.theme, text])
    blocked = _blocked_term_in(everything, rules.blocked_terms)
    if blocked:
        reasons.append(FlagReason(FlagCode.BLOCKED_WORD, f"blocked word: '{blocked}'"))

    quran = _first_match(_QURAN_PATTERNS, text)
    if quran:
        reasons.append(FlagReason(FlagCode.POSSIBLE_QURAN, f"possible Quran verse: '{quran}'"))

    hadith = _first_match(_HADITH_PATTERNS, text)
    if hadith:
        reasons.append(FlagReason(FlagCode.POSSIBLE_HADITH, f"possible hadith: '{hadith}'"))

    quoted = _long_quotation(text)
    if quoted:
        reasons.append(FlagReason(
            FlagCode.POSSIBLE_QUOTATION, f"possible Quran or hadith quotation: \"{quoted}\""))

    if _ARABIC.search(text):
        reasons.append(FlagReason(
            FlagCode.POSSIBLE_ARABIC, "contains Arabic text (possible Quran or hadith)"))

    if reasons:
        script = replace(script, status=ScriptStatus.FLAGGED)
    return ReviewResult(script=script, reasons=tuple(reasons))

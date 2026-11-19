"""The script pipeline: idea -> generate -> log draft -> review -> log flag.

Nothing here approves or publishes anything. The only statuses this code can
produce are DRAFT and FLAGGED; APPROVED is only ever set by a human, outside
this code. If a generator hands back a script already marked APPROVED, the
script is FLAGGED with the reason "generator returned a pre-approved script",
and that reason is logged.
"""

from dataclasses import replace

from src.ideas.model import Idea, IdeaStatus
from src.ideas.moderation import load_rules
from src.scripts.generator import ScriptGenerator, generate_script
from src.scripts.log import ScriptLog
from src.scripts.model import ScriptStatus
from src.scripts.review import FlagCode, FlagReason, ReviewResult, review_script

PRE_APPROVED_REASON = FlagReason(
    FlagCode.PRE_APPROVED, "generator returned a pre-approved script")


class IdeaNotEligibleError(Exception):
    """The idea has been removed, so no script is written for it."""


def run_script_pipeline(
    generator: ScriptGenerator,
    idea: Idea,
    log: ScriptLog,
    rules=None,
) -> ReviewResult:
    """Write, log and review a script for one idea.

    Returns a ReviewResult: the script (DRAFT or FLAGGED) and the reasons it
    was flagged, if any. Raises, and returns nothing, when:
      - the idea was REMOVED                      (IdeaNotEligibleError)
      - the generator gives no usable script      (ScriptGenerationError)
      - a save fails                              (ScriptSaveError)
    so a caller never receives a script that was not logged.

    Safe to run twice: the log ignores lines it already has, and the stub
    generator gives the same script for the same idea.
    """
    if idea.status == IdeaStatus.REMOVED:
        raise IdeaNotEligibleError(f"Idea {idea.id!r} was removed; no script is written for it")

    rules = rules if rules is not None else load_rules()

    script = generate_script(generator, idea)
    # Only a human approves. A generator that claims otherwise is flagged,
    # and the script is treated as a draft from here on.
    pre_approved = script.status == ScriptStatus.APPROVED
    script = replace(script, status=ScriptStatus.DRAFT)

    # Log the draft BEFORE reviewing it, so a crash can never lose a script.
    log.append(script)

    result = review_script(script, idea, rules)
    reasons = result.reasons
    if pre_approved:
        reasons = (PRE_APPROVED_REASON, *reasons)
        result = ReviewResult(
            script=replace(result.script, status=ScriptStatus.FLAGGED), reasons=reasons)
    if result.flagged:
        log.append(result.script, result.reasons)  # record the flag and why
    return result

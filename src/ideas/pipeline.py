"""The idea pipeline: generate -> log -> moderate -> log changes -> visible list.

Nothing here approves or publishes anything. APPROVED is only ever set by a
human, outside this code.
"""

from src.ideas.generator import IdeaGenerator, generate_ideas
from src.ideas.log import IdeaLog
from src.ideas.model import Idea, IdeaStatus
from src.ideas.moderation import Rules, apply_moderation, load_rules


def run_pipeline(
    generator: IdeaGenerator,
    prompt: str,
    log: IdeaLog,
    rules: Rules | None = None,
) -> list[Idea]:
    """Return the ideas a human should see: everything except REMOVED.

    Raises NoIdeasError (from generate_ideas) if the generator returns nothing.
    Safe to run twice: the log ignores lines it already has.
    """
    rules = rules if rules is not None else load_rules()

    ideas = generate_ideas(generator, prompt)

    # Log every idea BEFORE moderating, so a crash can never lose one.
    for idea in ideas:
        log.append(idea)

    visible = []
    for idea in ideas:
        moderated, _result = apply_moderation(idea, rules)
        if moderated.status != idea.status:
            log.append(moderated)  # record the status change (e.g. REMOVED, FLAGGED)
        if moderated.status != IdeaStatus.REMOVED:
            visible.append(moderated)
    return visible

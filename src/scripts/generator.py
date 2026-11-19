"""Script generation.

ScriptGenerator is the interface. The stub below needs no API key and no
network; a real AI generator can replace it later by providing the same
`generate(idea)` method. Use `generate_script()` to call any generator: it
refuses to hand back nothing, or a script written for a different idea.

A script that is only PARTLY filled in is still returned. Spotting and
flagging incomplete scripts is the job of the review step, not this one.
"""

import hashlib
from typing import Protocol

from src.ideas.model import Idea
from src.scripts.model import Script


class ScriptGenerationError(Exception):
    """A generator returned no usable script."""


class ScriptGenerator(Protocol):
    def generate(self, idea: Idea) -> Script:
        """Return a video script for the idea."""
        ...


def make_script_id(idea_id: str) -> str:
    """Deterministic id: the same idea always gives the same script id, so
    processing an idea twice cannot create two different scripts."""
    return "script-" + hashlib.sha256(idea_id.encode("utf-8")).hexdigest()[:12]


class StubScriptGenerator:
    """Builds a fixed, generic script from the idea's title and theme. It is
    not a real AI, and says so in the intro so nobody mistakes it for one."""

    def generate(self, idea: Idea) -> Script:
        return Script(
            id=make_script_id(idea.id),
            idea_id=idea.id,
            title=idea.title,
            theme=idea.theme,
            intro=f"(Stub draft, not real AI output.) Welcome. Today: {idea.title}.",
            sections=(
                f"Background: why {idea.theme} matters to us.",
                f"Main points about: {idea.title}.",
                "How we can apply this in daily life.",
            ),
            conclusion="Thank you for watching. Please check this script with a scholar.",
        )


def generate_script(generator: ScriptGenerator, idea: Idea) -> Script:
    script = generator.generate(idea)
    if script is None:
        raise ScriptGenerationError(f"The generator returned no script for idea {idea.id!r}")
    if script.idea_id != idea.id:
        raise ScriptGenerationError(
            f"The generator returned a script for idea {script.idea_id!r}, "
            f"but the idea was {idea.id!r}"
        )
    if len(script.missing_parts()) == 3:  # intro, sections and conclusion all empty
        raise ScriptGenerationError(f"The generator returned an empty script for idea {idea.id!r}")
    return script

"""The Script data model: one video script written for one video idea."""

from dataclasses import dataclass
from enum import Enum


class ScriptStatus(str, Enum):
    DRAFT = "draft"        # generated, waiting for a human to look at it
    FLAGGED = "flagged"    # a human must complete or check it before it goes further
    APPROVED = "approved"  # a human accepted it (only a human ever sets this)


@dataclass(frozen=True)
class Script:
    id: str
    idea_id: str   # the idea (src/ideas) this script was written for
    title: str
    theme: str
    intro: str = ""
    sections: tuple = ()   # the body, one string per section
    conclusion: str = ""
    status: ScriptStatus = ScriptStatus.DRAFT

    def missing_parts(self) -> tuple:
        """Names of the parts that are empty or blank. An empty tuple means
        the script is complete. This only checks that the parts exist, not
        that they are any good."""
        missing = []
        if not self.intro.strip():
            missing.append("intro")
        if not self.sections:
            missing.append("sections")
        elif any(not section.strip() for section in self.sections):
            missing.append("blank section")
        if not self.conclusion.strip():
            missing.append("conclusion")
        return tuple(missing)

    @property
    def is_complete(self) -> bool:
        return not self.missing_parts()

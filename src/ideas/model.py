"""The Idea data model: one proposed Islamic video idea."""

from dataclasses import dataclass
from enum import Enum


class IdeaStatus(str, Enum):
    PENDING = "pending"    # generated, waiting for a human to look at it
    FLAGGED = "flagged"    # moderation was unsure; a human must review it
    APPROVED = "approved"  # a human accepted it (only a human ever sets this)
    REMOVED = "removed"    # taken off the list (e.g. flagged as inappropriate)


@dataclass(frozen=True)
class Idea:
    id: str
    title: str
    theme: str
    status: IdeaStatus = IdeaStatus.PENDING

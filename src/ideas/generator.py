"""Idea generation.

IdeaGenerator is the interface. The stub below needs no API key and no
network; a real AI generator can replace it later by providing the same
`generate(prompt)` method. Use `generate_ideas()` to call any generator: it
refuses to return an empty list silently.
"""

import hashlib
from typing import Protocol

from src.ideas.model import Idea


class NoIdeasError(Exception):
    """A generator returned no ideas."""


class IdeaGenerator(Protocol):
    def generate(self, prompt: str) -> list[Idea]:
        """Return video ideas for the prompt."""
        ...


def make_idea_id(title: str, theme: str) -> str:
    """Deterministic id: the same title and theme always give the same id."""
    key = f"{title.strip().lower()}\n{theme.strip().lower()}"
    return "idea-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def make_idea(title: str, theme: str) -> Idea:
    return Idea(id=make_idea_id(title, theme), title=title, theme=theme)


# (title, theme) - one per allowed theme.
_STUB_IDEAS = (
    ("Five lessons from the Quran's opening chapter", "Quran"),
    ("The story behind a well-known hadith on kindness", "Hadith"),
    ("The patience of Prophet Ayyub", "Prophets"),
    ("A day in the life of the Prophet in Madinah", "Seerah"),
    ("How to find calm and focus in your prayer", "Salah"),
    ("Simple ways to make the most of Ramadan", "Ramadan"),
    ("A first-time pilgrim's guide to Hajj", "Hajj"),
    ("Everyday duas every child can learn", "Dua"),
    ("How the Abbasid House of Wisdom shaped learning", "Islamic History"),
    ("Honesty in business: lessons from the Prophet", "Character and Manners"),
    ("Shah-e-Hamdan and the spread of Islam in Kashmir", "Kashmiri Sufi Heritage"),
)


class StubIdeaGenerator:
    """Returns the same fixed ideas every time. It ignores the prompt."""

    def generate(self, prompt: str) -> list[Idea]:
        return [make_idea(title, theme) for title, theme in _STUB_IDEAS]


def generate_ideas(generator: IdeaGenerator, prompt: str) -> list[Idea]:
    ideas = generator.generate(prompt)
    if not ideas:
        raise NoIdeasError(f"The generator returned no ideas for prompt: {prompt!r}")
    return ideas

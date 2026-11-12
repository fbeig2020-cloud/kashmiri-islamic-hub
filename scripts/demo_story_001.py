"""Demo for STORY-001: generate -> log -> moderate -> visible list.

Run from the repo root:

    python scripts/demo_story_001.py

Safe to run twice: the log ignores lines it already has. Nothing is approved
or published. It writes only to data/ideas.jsonl (which git ignores).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ideas.generator import StubIdeaGenerator, make_idea  # noqa: E402
from src.ideas.log import IdeaLog  # noqa: E402
from src.ideas.pipeline import run_pipeline  # noqa: E402

LOG_PATH = REPO_ROOT / "data" / "ideas.jsonl"
PROMPT = "Video ideas for Kashmiri-speaking Muslims"
BAD_IDEA = make_idea("Mocking the fasting people", "Ramadan")


class DemoGenerator:
    """DEMO ONLY: the stub's ideas plus one deliberately inappropriate idea,
    so you can watch moderation remove it. Not a real AI generator."""

    def generate(self, prompt):
        return StubIdeaGenerator().generate(prompt) + [BAD_IDEA]


def heading(text):
    print(f"\n=== {text} ===")


def main():
    log = IdeaLog(LOG_PATH)

    heading("1. Visible ideas (REMOVED ones are hidden)")
    visible = run_pipeline(DemoGenerator(), PROMPT, log)
    for n, idea in enumerate(visible, start=1):
        print(f"{n:>2}. [{idea.status.value:<7}] {idea.title}  (theme: {idea.theme})")
    print(f"\n{len(visible)} ideas visible. Nothing is approved or published.")

    heading("2. The inappropriate demo idea")
    print(f'Demo idea: "{BAD_IDEA.title}"')
    if any(i.id == BAD_IDEA.id for i in visible):
        print("PROBLEM: it IS in the visible list.")
    else:
        print("It is NOT in the visible list.")

    heading(f"3. Log file: {LOG_PATH.relative_to(REPO_ROOT)}")
    entries = log.read()
    for n, entry in enumerate(entries, start=1):
        idea = entry["idea"]
        print(f"{n:>2}. {entry['logged_at']}  {idea['status']:<8} {idea['title']}  (theme: {idea['theme']})")
        print(f"      id: {idea['id']}   key: {entry['key']}")
    print(f"\n{len(entries)} log lines.")

    print("\nHistory of the inappropriate idea:")
    for entry in entries:
        if entry["idea"]["id"] == BAD_IDEA.id:
            print(f"  {entry['logged_at']}  -> {entry['idea']['status']}")


if __name__ == "__main__":
    main()

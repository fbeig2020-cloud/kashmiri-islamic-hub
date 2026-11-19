"""Demo for STORY-002: idea -> script -> review -> log.

Run from the repo root:

    python scripts/demo_story_002.py

It writes only to a TEMPORARY log that is deleted when the demo ends, never to
the real data/ folder. Nothing is approved or published, and the stub is not a
real AI. It shows:
  1. a video idea turning into a script
  2. an incomplete script flagged for human completion, with its reason
  3. every script in the log
  4. a second run writing nothing new
"""

import sys
import tempfile
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.ideas.generator import make_idea  # noqa: E402
from src.scripts.generator import StubScriptGenerator  # noqa: E402
from src.scripts.log import ScriptLog  # noqa: E402
from src.scripts.pipeline import run_script_pipeline  # noqa: E402

CLEAN_IDEA = make_idea("The patience of Prophet Ayyub", "Prophets")
QUOTE_IDEA = make_idea("The story behind a well-known hadith on kindness", "Hadith")
INCOMPLETE_IDEA = make_idea("Simple ways to make the most of Ramadan", "Ramadan")
IDEAS = (CLEAN_IDEA, QUOTE_IDEA, INCOMPLETE_IDEA)


class DemoGenerator:
    """DEMO ONLY: the stub, except that for one idea it returns a script with
    no sections and no conclusion, so you can watch review flag it. A real AI
    could do this by running out of space or losing its way."""

    def generate(self, idea):
        script = StubScriptGenerator().generate(idea)
        if idea.id == INCOMPLETE_IDEA.id:
            return replace(script, sections=(), conclusion="")
        return script


def heading(text):
    print(f"\n=== {text} ===")


def run_all(log):
    return [run_script_pipeline(DemoGenerator(), idea, log) for idea in IDEAS]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        log = ScriptLog(Path(tmp) / "scripts.jsonl")
        print("Using a temporary log (deleted at the end). The real data/ is not touched.")

        results = run_all(log)

        heading("1. A video idea turning into a script")
        idea, result = CLEAN_IDEA, results[0]
        print(f'Idea:   "{idea.title}"  (theme: {idea.theme})')
        print(f"Script: {result.script.id}   status: {result.script.status.value}")
        print(f"  Intro:      {result.script.intro}")
        for n, section in enumerate(result.script.sections, start=1):
            print(f"  Section {n}:  {section}")
        print(f"  Conclusion: {result.script.conclusion}")
        print("It stays a draft: nothing is approved. A person decides.")

        heading("2. An incomplete script, flagged for human completion")
        idea, result = INCOMPLETE_IDEA, results[2]
        print(f'Idea:   "{idea.title}"')
        print(f"Script: {result.script.id}   status: {result.script.status.value}")
        print(f"  Intro:      {result.script.intro!r}")
        print(f"  Sections:   {list(result.script.sections)}")
        print(f"  Conclusion: {result.script.conclusion!r}")
        for reason in result.reasons:
            print(f"  FLAGGED because: {reason.detail}")

        print("\nAlso flagged: a script that may quote a hadith, for a human to check.")
        for reason in results[1].reasons:
            print(f"  {results[1].script.id}  FLAGGED because: {reason.detail}")

        heading("3. Every script in the log")
        entries = log.read()
        for n, entry in enumerate(entries, start=1):
            script = entry["script"]
            print(f"{n:>2}. {entry['logged_at']}  {script['status']:<8} {script['title']}")
            print(f"      id: {script['id']}   key: {entry['key']}")
            for reason in entry["reasons"]:
                print(f"      reason: [{reason['code']}] {reason['detail']}")
        print(f"\n{len(entries)} log lines.")

        heading("4. A second run writes nothing new")
        before = log.path.read_bytes()
        run_all(log)
        after = log.path.read_bytes()
        print(f"Log lines before: {len(before.splitlines())}   after: {len(after.splitlines())}")
        print("Log file unchanged." if before == after else "PROBLEM: the log changed.")

        statuses = {entry["script"]["status"] for entry in log.read()}
        print(f"\nStatuses in the log: {sorted(statuses)}  (never 'approved')")


if __name__ == "__main__":
    main()

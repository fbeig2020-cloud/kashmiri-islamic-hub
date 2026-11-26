"""Demo for STORY-003: flag -> human review -> log.

Run from the repo root:

    python scripts/demo_story_003.py

It works only in a TEMPORARY folder that is deleted when the demo ends, never
in the real data/ folder. The scripts come from a stub, not a real AI, the
reviewer names are made up, and nothing is published.
"""

import contextlib
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import review_scripts  # noqa: E402  (the command-line script, next to this file)
from src.ideas.generator import make_idea  # noqa: E402
from src.scripts.generator import StubScriptGenerator, make_script_id  # noqa: E402
from src.scripts.log import ScriptLog, ScriptSaveError  # noqa: E402
from src.scripts.pipeline import run_script_pipeline  # noqa: E402

HADITH = make_idea("The story behind a well-known hadith on kindness", "Hadith")
VERSE = make_idea("Lessons from Surah Yusuf", "Quran")
INCOMPLETE = make_idea("Simple ways to make the most of Ramadan", "Ramadan")
CRASHED = make_idea("A hadith about being a good neighbour", "Hadith")


def script_id(idea):
    return make_script_id(idea.id)


class DemoGenerator:
    """DEMO ONLY: the stub, except that one script comes back unfinished."""

    def generate(self, idea):
        script = StubScriptGenerator().generate(idea)
        if idea.id == INCOMPLETE.id:
            return replace(script, conclusion="")
        return script


class CrashesBeforeFlagging(ScriptLog):
    """DEMO ONLY: saves the draft, then fails when saving the flag."""

    saves = 0

    def append(self, script, reasons=(), now=None):
        self.saves += 1
        if self.saves == 2:
            raise ScriptSaveError("simulated crash")
        return super().append(script, reasons, now)


def heading(text):
    print(f"\n=== {text} ===")


def command(data, *args):
    """Run the real command-line script and show what it prints."""
    print("\n$ review_scripts.py " + " ".join(f'"{a}"' if " " in a else a for a in args))
    with contextlib.redirect_stderr(sys.stdout):
        code = review_scripts.main(["--data-dir", str(data), *args])
    print(f"(exit code {code})")


def statuses(log, idea):
    return [e["script"]["status"] for e in log.read() if e["script"]["id"] == script_id(idea)]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        log = ScriptLog(data / "scripts.jsonl")
        print("Using a temporary folder (deleted at the end). The real data/ is not touched.")

        heading("1. Uncertain scripts are flagged")
        for idea in (HADITH, VERSE, INCOMPLETE):
            result = run_script_pipeline(DemoGenerator(), idea, log)
            reasons = "; ".join(r.detail for r in result.reasons)
            print(f"{result.script.id}  {result.script.status.value}  {reasons}")
        command(data, "list")

        heading("2. A reviewer approves one and rejects another")
        command(data, "approve", script_id(HADITH), "--reviewer", "Aisha",
                "--note", "Checked against the source.")
        command(data, "reject", script_id(VERSE), "--reviewer", "Bilal",
                "--note", "No verse is actually given.")

        heading("3. An incomplete script cannot be approved, only rejected")
        command(data, "approve", script_id(INCOMPLETE), "--reviewer", "Aisha")
        command(data, "reject", script_id(INCOMPLETE), "--reviewer", "Aisha")

        heading("4. Decisions are final")
        command(data, "approve", script_id(HADITH), "--reviewer", "Aisha")
        command(data, "reject", script_id(HADITH), "--reviewer", "Bilal")

        heading("5. A crash while flagging is recovered")
        try:
            run_script_pipeline(DemoGenerator(), CRASHED, CrashesBeforeFlagging(log.path))
        except ScriptSaveError as err:
            print(f"Pipeline stopped: {err}")
        print(f"Logged for this script: {statuses(log, CRASHED)}")
        command(data, "list")
        print(f"Logged for this script: {statuses(log, CRASHED)}")
        before = log.path.read_bytes()
        review_scripts.ReviewQueue(log, review_scripts.ActionLog(
            data / "review_actions.jsonl")).items()
        print("Listing again: " + ("script log unchanged."
                                   if log.path.read_bytes() == before else "PROBLEM: changed."))

        heading("6. What is on record")
        print("Flagged items (scripts.jsonl):")
        for entry in log.read():
            if entry["script"]["status"] == "flagged":
                codes = ", ".join(r["code"] for r in entry["reasons"])
                print(f"  {entry['logged_at']}  {entry['script']['id']}  [{codes}]")
        print("\nReviewer actions (review_actions.jsonl):")
        for line in (data / "review_actions.jsonl").read_text(encoding="utf-8").splitlines():
            action = json.loads(line)
            print(f"  {action['decided_at']}  {action['script_id']}  {action['decision']:<8} "
                  f"by {action['reviewer']}  {action['note']}")
        print("\nRefused attempts are not recorded. Nothing was published.")


if __name__ == "__main__":
    main()

"""Review flagged video scripts from the command line.

Run from anywhere; it uses the repo's data/ folder:

    python scripts/review_scripts.py list [--all]
    python scripts/review_scripts.py approve <script_id> --reviewer "Name" [--note "..."]
    python scripts/review_scripts.py reject  <script_id> --reviewer "Name" [--note "..."]

--data-dir (before the command) points at another folder, for tests and demos.

Exit code 0: done, or the same decision was already recorded.
Exit code 1: refused, or a log could not be read or saved.
Exit code 2: the command was typed wrongly.

The reviewer name is not checked (there is no login). Approving publishes
nothing.
"""

import argparse
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.scripts.action_log import ActionLog, ActionSaveError  # noqa: E402
from src.scripts.actions import Decision, ReviewActionError  # noqa: E402
from src.scripts.log import ScriptLog, ScriptSaveError  # noqa: E402
from src.scripts.review_queue import PENDING, QueueReadError, ReviewQueue  # noqa: E402

DEFAULT_DATA_DIR = REPO_ROOT / "data"
DECISIONS = {"approve": Decision.APPROVED, "reject": Decision.REJECTED}


def clean(text: str) -> str:
    """Show control characters instead of obeying them, so script text cannot
    hide or overwrite what the reviewer sees."""
    return "".join(
        repr(c)[1:-1] if unicodedata.category(c) == "Cc" and c not in "\n\t" else c
        for c in text
    )


def show(label: str, text: str) -> None:
    first, *rest = clean(text).split("\n")
    print(f"  {label:<12}{first}")
    for line in rest:
        print(f"  {'':<12}{line}")


def print_item(item) -> None:
    script = item.script
    print(f"\n{clean(script.id)}  [{item.status}]")
    show("Title:", script.title)
    show("Theme:", script.theme)
    show("Intro:", script.intro or "(missing)")
    for number, section in enumerate(script.sections, start=1):
        show(f"Section {number}:", section or "(blank)")
    if not script.sections:
        show("Sections:", "(missing)")
    show("Conclusion:", script.conclusion or "(missing)")
    for reason in item.reasons:
        show("Flagged:", f"[{reason.code.value}] {reason.detail}")
    if item.action:
        action = item.action
        show("Decided:", f"{action.decision.value} by {action.reviewer} "
                         f"at {action.decided_at.isoformat()}")
        if action.note:
            show("Note:", action.note)


def list_items(queue, data_dir, include_decided) -> None:
    items = queue.items()
    if not include_decided:
        items = [item for item in items if item.status == PENDING]
    kind = "flagged" if include_decided else "pending flagged"
    print(f"{len(items)} {kind} script(s) in {data_dir}")
    for item in items:
        print_item(item)


def record(queue, command, script_id, reviewer, note) -> None:
    # Look the script up BEFORE saving, so nothing can fail after the save and
    # make a recorded decision look unrecorded.
    item = next((i for i in queue.items() if i.script.id == script_id), None)

    if not queue.review(script_id, DECISIONS[command], reviewer, note):
        print("already decided, nothing changed")
        return

    print("Decision saved.")
    show("Script:", script_id)
    show("Title:", item.script.title)
    show("Decision:", DECISIONS[command].value)
    show("Reviewer:", reviewer.strip())
    for reason in item.reasons:
        show("Flagged:", f"[{reason.code.value}] {reason.detail}")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Review flagged video scripts.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list", help="show flagged scripts")
    listing.add_argument("--all", action="store_true", help="include decided scripts")
    for name in DECISIONS:
        sub = commands.add_parser(name, help=f"{name} one flagged script")
        sub.add_argument("script_id")
        sub.add_argument("--reviewer", required=True, help="your name")
        sub.add_argument("--note", default="")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    # Windows terminals often default to an encoding that cannot print Arabic.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = parse_args(argv)
    try:
        try:
            queue = ReviewQueue(
                ScriptLog(args.data_dir / "scripts.jsonl"),
                ActionLog(args.data_dir / "review_actions.jsonl"),
            )
        except (OSError, ValueError, KeyError) as err:
            print(f"Error: could not load the moderation rules: {err}", file=sys.stderr)
            return 1

        if args.command == "list":
            list_items(queue, args.data_dir, args.all)
        else:
            record(queue, args.command, args.script_id, args.reviewer, args.note)
    except (ReviewActionError, QueueReadError, ActionSaveError, ScriptSaveError) as err:
        print(f"Error: {clean(str(err))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

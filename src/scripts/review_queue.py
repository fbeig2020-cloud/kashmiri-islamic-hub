"""The review queue: what reviewers see, and how their decision is recorded.

items()   every flagged script, with its full text, the flag reasons and
          whether it is pending, approved or rejected
review()  load one script, apply the rules (actions.py), save the decision
          (action_log.py)

Recovery after a crash while flagging:
  The pipeline logs the draft first and the flag second. If it stops in
  between, only the draft is logged. So items() runs the review checks again on
  every script that has a draft line and no flag line, and writes the missing
  flag line for those that should have one. Listing twice writes nothing new.
  A change to the rules or blocklist therefore also flags older drafts.

If a log cannot be read this raises QueueReadError, never an empty list. If a
recovered flag cannot be saved, ScriptSaveError is raised.

KNOWN LIMITS:
  - A script that was flagged ONLY because the generator marked it approved
    (pre_approved) is NOT recovered: the draft line does not record that. It
    stays out of the list until the pipeline is run again for that idea. If it
    had other reasons too, it is recovered with those, without pre_approved.
  - Recovery only has the script's title and theme, not the idea's. If a
    generator changed them, a blocked word in the idea alone is missed.
"""

from dataclasses import dataclass

from src.ideas.model import Idea
from src.ideas.moderation import load_rules
from src.scripts.action_log import ActionLog
from src.scripts.actions import Decision, decide
from src.scripts.log import ScriptLog
from src.scripts.model import Script, ScriptStatus
from src.scripts.review import FlagCode, FlagReason, review_script

PENDING = "pending"


class QueueReadError(Exception):
    """The script log or the decision log could not be read."""


@dataclass(frozen=True)
class ReviewItem:
    script: Script   # the text as logged when it was flagged
    reasons: tuple   # of FlagReason
    action: object = None  # the ReviewAction, or None while pending

    @property
    def status(self) -> str:
        return self.action.decision.value if self.action else PENDING


def _to_script(data: dict) -> Script:
    return Script(
        id=data["id"],
        idea_id=data["idea_id"],
        title=data["title"],
        theme=data["theme"],
        intro=data["intro"],
        sections=tuple(data["sections"]),
        conclusion=data["conclusion"],
        status=ScriptStatus(data["status"]),
    )


class ReviewQueue:
    def __init__(self, script_log=None, action_log=None, rules=None):
        self.script_log = script_log or ScriptLog()
        self.action_log = action_log or ActionLog()
        self.rules = rules if rules is not None else load_rules()

    def items(self) -> list:
        """All flagged scripts, in the order they were logged, after recovering
        any missing flag lines."""
        drafts, flagged = self._logged_scripts()

        for script_id, script in drafts.items():
            if script_id in flagged:
                continue
            idea = Idea(id=script.idea_id, title=script.title, theme=script.theme)
            result = review_script(script, idea, self.rules)
            if result.flagged:
                # ScriptLog ignores a line it already has, so this cannot
                # create a second flag line.
                self.script_log.append(result.script, result.reasons)
                flagged[script_id] = (result.script, result.reasons)

        try:
            return [
                ReviewItem(script, reasons, self.action_log.get(script_id))
                for script_id, (script, reasons) in flagged.items()
            ]
        except (OSError, ValueError) as err:
            raise QueueReadError(f"Could not read the decision log: {err}") from err

    def review(self, script_id: str, decision: Decision, reviewer: str, note: str = "") -> bool:
        """Record one reviewer's decision.

        Returns True if it was recorded, False if this identical decision
        already was. Raises a ReviewActionError if the rules refuse it,
        QueueReadError if a log cannot be read, and ActionSaveError or
        ScriptSaveError if something cannot be saved.
        """
        item = next((i for i in self.items() if i.script.id == script_id), None)
        if item is not None:
            script, codes, existing = item.script, [r.code for r in item.reasons], item.action
        else:  # not flagged: either a clean draft or an unknown id
            script, codes, existing = self._logged_scripts()[0].get(script_id), [], None

        action = decide(script_id, script, codes, decision, reviewer, existing, note)
        if action is None:
            return False
        return self.action_log.append(action)

    def _logged_scripts(self):
        """({id: draft script}, {id: (flagged script, reasons)}) from the log."""
        drafts, flagged = {}, {}
        try:
            for entry in self.script_log.read():
                script = _to_script(entry["script"])
                if script.status == ScriptStatus.DRAFT:
                    drafts[script.id] = script
                elif script.status == ScriptStatus.FLAGGED:
                    flagged[script.id] = (script, tuple(
                        FlagReason(FlagCode(r["code"]), r["detail"]) for r in entry["reasons"]))
        except (OSError, ValueError, KeyError, TypeError) as err:
            raise QueueReadError(f"Could not read the script log: {err}") from err
        return drafts, flagged

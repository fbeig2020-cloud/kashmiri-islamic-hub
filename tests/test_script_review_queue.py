import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.ideas.generator import make_idea
from src.scripts.action_log import ActionLog, ActionSaveError
from src.scripts.actions import (
    AlreadyDecidedError,
    Decision,
    IncompleteScriptError,
    NotFlaggedError,
    UnknownScriptError,
)
from src.scripts.generator import StubScriptGenerator, make_script_id
from src.scripts.log import ScriptLog, ScriptSaveError
from src.scripts.model import ScriptStatus
from src.scripts.pipeline import run_script_pipeline
from src.scripts.review_queue import QueueReadError, ReviewQueue

CLEAN_IDEA = make_idea("The patience of Prophet Ayyub", "Prophets")
HADITH_IDEA = make_idea("The story behind a well-known hadith on kindness", "Hadith")
CLEAN_ID = make_script_id(CLEAN_IDEA.id)
HADITH_ID = make_script_id(HADITH_IDEA.id)


class ChangedStub:
    """The stub generator with some fields changed."""

    def __init__(self, **changes):
        self.changes = changes

    def generate(self, idea):
        return replace(StubScriptGenerator().generate(idea), **self.changes)


class CrashesBeforeFlagging(ScriptLog):
    """Saves the draft, then fails on the second save, like a crash."""

    saves = 0

    def append(self, script, reasons=(), now=None):
        self.saves += 1
        if self.saves == 2:
            raise ScriptSaveError("crash")
        return super().append(script, reasons, now)


class QueueTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        folder = Path(self._tmp.name) / "data"  # never the real data/
        self.script_path = folder / "scripts.jsonl"
        self.action_path = folder / "review_actions.jsonl"
        self.script_log = ScriptLog(self.script_path)
        self.queue = ReviewQueue(self.script_log, ActionLog(self.action_path))

    def run_pipeline(self, idea, generator=None, log=None):
        return run_script_pipeline(generator or StubScriptGenerator(), idea, log or self.script_log)

    def crash_while_flagging(self, idea, generator=None):
        with self.assertRaises(ScriptSaveError):
            self.run_pipeline(idea, generator, CrashesBeforeFlagging(self.script_path))
        self.assertEqual(self.logged(), ["draft"])

    def logged(self):
        return [e["script"]["status"] for e in self.script_log.read()]


class ListAndReviewTest(QueueTestCase):
    def test_only_flagged_scripts_are_listed_with_text_reasons_and_status(self):
        self.run_pipeline(CLEAN_IDEA)
        flagged = self.run_pipeline(HADITH_IDEA)

        [item] = self.queue.items()

        self.assertEqual(item.script, flagged.script)
        self.assertEqual(item.reasons, flagged.reasons)
        self.assertEqual(item.status, "pending")

    def test_nothing_logged_yet_gives_an_empty_list(self):
        self.assertEqual(self.queue.items(), [])

    def test_approve_and_reject_are_recorded_and_shown(self):
        incomplete_idea = make_idea("Making the most of Ramadan", "Ramadan")
        self.run_pipeline(HADITH_IDEA)
        self.run_pipeline(incomplete_idea, ChangedStub(conclusion=""))
        incomplete_id = make_script_id(incomplete_idea.id)

        self.assertTrue(self.queue.review(HADITH_ID, Decision.APPROVED, " Aisha ", "checked"))
        self.assertTrue(self.queue.review(incomplete_id, Decision.REJECTED, "Bilal"))

        first, second = self.queue.items()
        self.assertEqual((first.status, first.action.reviewer, first.action.note),
                         ("approved", "Aisha", "checked"))
        self.assertEqual((second.status, second.action.reviewer), ("rejected", "Bilal"))

    def test_repeat_records_nothing_and_a_different_decision_raises(self):
        self.run_pipeline(HADITH_IDEA)
        self.queue.review(HADITH_ID, Decision.REJECTED, "Aisha")
        before = self.action_path.read_bytes()

        self.assertFalse(self.queue.review(HADITH_ID, Decision.REJECTED, "Aisha "))
        with self.assertRaises(AlreadyDecidedError):
            self.queue.review(HADITH_ID, Decision.APPROVED, "Aisha")

        self.assertEqual(self.action_path.read_bytes(), before)

    def test_refused_decisions_save_nothing(self):
        incomplete_idea = make_idea("Making the most of Ramadan", "Ramadan")
        self.run_pipeline(CLEAN_IDEA)
        self.run_pipeline(incomplete_idea, ChangedStub(conclusion=""))

        for error, script_id in (
            (NotFlaggedError, CLEAN_ID),
            (UnknownScriptError, "script-nope"),
            (IncompleteScriptError, make_script_id(incomplete_idea.id)),
        ):
            with self.subTest(error=error.__name__):
                with self.assertRaises(error):
                    self.queue.review(script_id, Decision.APPROVED, "Aisha")

        self.assertFalse(self.action_path.exists())

    def test_failed_save_of_a_decision_raises_and_the_item_stays_pending(self):
        self.run_pipeline(HADITH_IDEA)
        self.action_path.parent.joinpath("blocker").write_text("x")
        queue = ReviewQueue(
            self.script_log, ActionLog(self.action_path.parent / "blocker" / "actions.jsonl"))

        with self.assertRaises(ActionSaveError):
            queue.review(HADITH_ID, Decision.APPROVED, "Aisha")

        self.assertEqual(self.queue.items()[0].status, "pending")


class CrashRecoveryTest(QueueTestCase):
    def test_crash_while_flagging_is_recovered_with_exactly_one_flag_line(self):
        self.crash_while_flagging(HADITH_IDEA)

        [item] = self.queue.items()

        self.assertEqual(item.script.id, HADITH_ID)
        self.assertEqual(item.script.status, ScriptStatus.FLAGGED)
        self.assertEqual([r.code.value for r in item.reasons], ["possible_hadith"])
        self.assertEqual(self.logged(), ["draft", "flagged"])

        after_first = self.script_path.read_bytes()
        self.assertEqual(self.queue.items(), [item])  # listing again
        self.run_pipeline(HADITH_IDEA)                # and re-running the pipeline
        self.assertEqual(self.script_path.read_bytes(), after_first)

    def test_a_recovered_script_can_be_reviewed_without_listing_first(self):
        self.crash_while_flagging(HADITH_IDEA)

        self.assertTrue(self.queue.review(HADITH_ID, Decision.APPROVED, "Aisha"))

        self.assertEqual(self.logged(), ["draft", "flagged"])

    def test_pre_approved_only_is_not_recovered(self):
        """A known limit: nothing in the draft line says why it was flagged."""
        generator = ChangedStub(status=ScriptStatus.APPROVED)
        self.crash_while_flagging(CLEAN_IDEA, generator)

        self.assertEqual(self.queue.items(), [])
        self.assertEqual(self.logged(), ["draft"])
        with self.assertRaises(NotFlaggedError):
            self.queue.review(CLEAN_ID, Decision.APPROVED, "Aisha")

        self.run_pipeline(CLEAN_IDEA, generator)  # the only way back

        [item] = self.queue.items()
        self.assertEqual([r.code.value for r in item.reasons], ["pre_approved"])

    def test_failed_recovery_save_raises_instead_of_hiding_the_script(self):
        self.crash_while_flagging(HADITH_IDEA)
        log = CrashesBeforeFlagging(self.script_path)
        log.saves = 1  # the next save fails

        with self.assertRaises(ScriptSaveError):
            ReviewQueue(log, ActionLog(self.action_path)).items()


class UnreadableLogTest(QueueTestCase):
    def test_corrupt_script_log_raises_instead_of_an_empty_list(self):
        self.script_path.parent.mkdir(parents=True)
        for content in (b"not json\n", b'{"key": "x"}\n'):
            with self.subTest(content=content):
                self.script_path.write_bytes(content)

                with self.assertRaises(QueueReadError):
                    self.queue.items()

    def test_script_log_that_cannot_be_opened_raises(self):
        self.script_path.mkdir(parents=True)  # a folder where the file should be

        with self.assertRaises(QueueReadError):
            self.queue.items()

    def test_corrupt_decision_log_raises_instead_of_showing_pending(self):
        self.run_pipeline(HADITH_IDEA)
        self.action_path.write_bytes(b"not json\n")

        with self.assertRaises(QueueReadError):
            self.queue.items()


if __name__ == "__main__":
    unittest.main()

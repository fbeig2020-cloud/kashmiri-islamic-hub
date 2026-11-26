import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from src.scripts.action_log import ActionLog, ActionSaveError
from src.scripts.actions import (
    AlreadyDecidedError,
    Decision,
    InvalidReviewerError,
    ReviewAction,
)

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def an_action(**changes):
    fields = dict(
        script_id="script-a",
        decision=Decision.APPROVED,
        reviewer="Aisha",
        content_hash="hash-1",
        decided_at=NOW,
        note="Checked the source. بسم الله",
    )
    fields.update(changes)
    return ReviewAction(**fields)


class ActionLogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "data" / "review_actions.jsonl"  # never the real data/
        self.log = ActionLog(self.path)

    # saving and reading back

    def test_decision_is_read_back_by_script_id(self):
        first = an_action()
        second = an_action(script_id="script-b", decision=Decision.REJECTED)

        self.assertTrue(self.log.append(first))
        self.assertTrue(self.log.append(second))

        self.assertEqual(ActionLog(self.path).get("script-a"), first)
        self.assertEqual(ActionLog(self.path).get("script-b"), second)
        self.assertIsNone(self.log.get("script-z"))

    def test_missing_log_has_no_decisions(self):
        self.assertEqual(self.log.read(), [])
        self.assertIsNone(self.log.get("script-a"))

    # repeats and conflicts

    def test_identical_repeat_is_a_no_op(self):
        self.log.append(an_action())
        before = self.path.read_bytes()
        later = an_action(note="another note", decided_at=datetime.now(timezone.utc))

        self.assertFalse(self.log.append(later))

        self.assertEqual(self.path.read_bytes(), before)

    def test_different_decision_raises_and_names_who_and_what(self):
        self.log.append(an_action())
        before = self.path.read_bytes()

        for name, other in (
            ("other outcome", an_action(decision=Decision.REJECTED)),
            ("other reviewer", an_action(reviewer="Bilal")),
            ("other text", an_action(content_hash="hash-2")),
        ):
            with self.subTest(name):
                with self.assertRaises(AlreadyDecidedError) as caught:
                    self.log.append(other)

                self.assertIn("approved", str(caught.exception))
                self.assertIn("'Aisha'", str(caught.exception))
                self.assertEqual(self.path.read_bytes(), before)

    # reviewer names

    def test_spaces_around_the_reviewer_name_are_trimmed(self):
        self.log.append(an_action(reviewer="  Aisha  "))

        self.assertIn('"reviewer": "Aisha"', self.path.read_text(encoding="utf-8"))
        self.assertFalse(self.log.append(an_action(reviewer="Aisha ")))

    def test_blank_reviewer_is_not_saved(self):
        with self.assertRaises(InvalidReviewerError):
            self.log.append(an_action(reviewer="   "))

        self.assertEqual(self.log.read(), [])

    # failures

    def test_failing_save_raises_and_a_retry_after_the_fault_still_saves(self):
        with mock.patch("builtins.open", side_effect=PermissionError("disk is read-only")):
            with self.assertRaises(ActionSaveError) as caught:
                self.log.append(an_action())

        self.assertIn("script-a", str(caught.exception))
        self.assertIsNone(self.log.get("script-a"))
        self.assertTrue(self.log.append(an_action()))

    def test_folder_that_cannot_be_created_raises(self):
        (self.dir / "data").write_text("not a folder")

        with self.assertRaises(ActionSaveError):
            self.log.append(an_action())

    def test_corrupt_log_raises_on_read_and_on_save(self):
        self.path.parent.mkdir(parents=True)
        for content in (b"not json\n", b'{"script_id": "script-a"}\n', b"[]\n"):
            with self.subTest(content=content):
                self.path.write_bytes(content)

                with self.assertRaises(ValueError):
                    self.log.get("script-a")
                with self.assertRaises(ActionSaveError):
                    self.log.append(an_action())
                self.assertEqual(self.path.read_bytes(), content)

    # crash safety

    def test_half_written_last_line_is_skipped_and_cleaned_up_on_next_save(self):
        self.log.append(an_action())
        with open(self.path, "ab") as f:  # simulate a crash mid-write
            f.write(b'{"script_id": "script-b", "decision": "appr')

        self.assertEqual([a.script_id for a in self.log.read()], ["script-a"])
        self.assertIsNone(self.log.get("script-b"))

        self.assertTrue(self.log.append(replace(an_action(), script_id="script-b")))
        self.assertEqual([a.script_id for a in self.log.read()], ["script-a", "script-b"])
        self.assertEqual(len(self.path.read_bytes().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()

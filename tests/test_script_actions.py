import unittest
from dataclasses import replace
from datetime import datetime, timezone

from src.scripts.actions import (
    AlreadyDecidedError,
    Decision,
    IncompleteScriptError,
    InvalidReviewerError,
    NotFlaggedError,
    UnknownScriptError,
    content_hash,
    decide,
)
from src.scripts.model import Script, ScriptStatus
from src.scripts.review import FlagCode

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

FLAGGED = Script(
    id="script-1",
    idea_id="idea-1",
    title="A hadith on kindness",
    theme="Hadith",
    intro="Welcome.",
    sections=("There is a hadith about this.",),
    conclusion="Thank you.",
    status=ScriptStatus.FLAGGED,
)


def review(decision, script=FLAGGED, codes=("possible_hadith",), reviewer="Aisha", **kwargs):
    return decide("script-1", script, codes, decision, reviewer, now=NOW, **kwargs)


class AllowedChangesTest(unittest.TestCase):
    def test_flagged_script_can_be_approved_or_rejected(self):
        for decision in Decision:
            with self.subTest(decision=decision):
                action = review(decision, note="  checked  ")

                self.assertEqual(action.script_id, "script-1")
                self.assertEqual(action.decision, decision)
                self.assertEqual(action.reviewer, "Aisha")
                self.assertEqual(action.note, "checked")
                self.assertEqual(action.decided_at, NOW)
                self.assertEqual(action.content_hash, content_hash(FLAGGED))

    def test_every_reason_except_missing_parts_can_be_approved(self):
        for code in FlagCode:
            if code == FlagCode.MISSING_PARTS:
                continue
            with self.subTest(code=code):
                self.assertEqual(
                    review(Decision.APPROVED, codes=(code,)).decision, Decision.APPROVED)

    def test_deciding_does_not_change_the_script(self):
        review(Decision.APPROVED)

        self.assertEqual(FLAGGED.status, ScriptStatus.FLAGGED)


class MissingPartsTest(unittest.TestCase):
    INCOMPLETE = replace(FLAGGED, conclusion="")

    def test_missing_parts_cannot_be_approved_even_with_other_reasons(self):
        for codes in (("missing_parts",), (FlagCode.POSSIBLE_HADITH, FlagCode.MISSING_PARTS)):
            with self.subTest(codes=codes):
                with self.assertRaises(IncompleteScriptError):
                    review(Decision.APPROVED, script=self.INCOMPLETE, codes=codes)

    def test_the_reason_alone_blocks_approval(self):
        with self.assertRaises(IncompleteScriptError):
            review(Decision.APPROVED, codes=("missing_parts",))

    def test_an_incomplete_script_blocks_approval_even_if_the_reason_is_lost(self):
        with self.assertRaises(IncompleteScriptError):
            review(Decision.APPROVED, script=self.INCOMPLETE, codes=())

    def test_missing_parts_can_be_rejected(self):
        action = review(Decision.REJECTED, script=self.INCOMPLETE, codes=("missing_parts",))

        self.assertEqual(action.decision, Decision.REJECTED)


class RefusedTest(unittest.TestCase):
    def test_unknown_script(self):
        with self.assertRaises(UnknownScriptError) as caught:
            review(Decision.APPROVED, script=None)

        self.assertIn("script-1", str(caught.exception))

    def test_script_that_is_not_flagged(self):
        for status in (ScriptStatus.DRAFT, ScriptStatus.APPROVED):
            for decision in Decision:
                with self.subTest(status=status, decision=decision):
                    with self.assertRaises(NotFlaggedError):
                        review(decision, script=replace(FLAGGED, status=status))

    def test_blank_reviewer(self):
        for name in ("", "   ", None):
            with self.subTest(name=name):
                with self.assertRaises(InvalidReviewerError):
                    review(Decision.APPROVED, reviewer=name)

    def test_decision_other_than_approved_or_rejected(self):
        with self.assertRaises(ValueError):
            review("published")

    def test_script_or_earlier_decision_for_another_id(self):
        other = replace(FLAGGED, id="script-2")
        with self.assertRaises(ValueError):
            review(Decision.APPROVED, script=other)

        others_action = decide("script-2", other, (), Decision.APPROVED, "Aisha")
        with self.assertRaises(ValueError):
            review(Decision.APPROVED, existing=others_action)


class DecisionsAreFinalTest(unittest.TestCase):
    def test_repeating_the_same_decision_records_nothing_new(self):
        for decision in Decision:
            with self.subTest(decision=decision):
                first = review(decision)

                again = review(decision, reviewer=" Aisha ", note="new note", existing=first)

                self.assertIsNone(again)

    def test_a_decision_cannot_be_reversed(self):
        for first, second in ((Decision.APPROVED, Decision.REJECTED),
                              (Decision.REJECTED, Decision.APPROVED)):
            with self.subTest(first=first):
                with self.assertRaises(AlreadyDecidedError) as caught:
                    review(second, existing=review(first))

                self.assertIn("Aisha", str(caught.exception))

    def test_another_reviewer_cannot_decide_again(self):
        with self.assertRaises(AlreadyDecidedError):
            review(Decision.APPROVED, reviewer="Bilal", existing=review(Decision.APPROVED))

    def test_a_regenerated_script_with_the_same_id_cannot_be_approved(self):
        rejected = review(Decision.REJECTED)
        new_text = replace(FLAGGED, intro="A rewritten welcome.")

        for decision in Decision:
            with self.subTest(decision=decision):
                with self.assertRaises(AlreadyDecidedError) as caught:
                    review(decision, script=new_text, existing=rejected)

                self.assertIn("different text", str(caught.exception))


class ContentHashTest(unittest.TestCase):
    def test_hash_follows_the_text_and_ignores_the_status(self):
        self.assertEqual(
            content_hash(FLAGGED), content_hash(replace(FLAGGED, status=ScriptStatus.DRAFT)))
        self.assertNotEqual(
            content_hash(FLAGGED), content_hash(replace(FLAGGED, conclusion="Bye.")))


if __name__ == "__main__":
    unittest.main()

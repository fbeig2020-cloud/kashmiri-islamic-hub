import unittest

from src.ideas.generator import make_idea
from src.ideas.moderation import load_rules
from src.scripts.generator import StubScriptGenerator, generate_script
from src.scripts.model import Script, ScriptStatus
from src.scripts.review import FlagCode, review_script

RULES = load_rules()
IDEA = make_idea("The patience of Prophet Ayyub", "Prophets")


def script_with(**changes):
    fields = dict(
        id="script-1",
        idea_id=IDEA.id,
        title=IDEA.title,
        theme=IDEA.theme,
        intro="Welcome to this short talk.",
        sections=("Who Ayyub was.", "How he stayed patient."),
        conclusion="Thank you for watching.",
    )
    fields.update(changes)
    return Script(**fields)


def codes(result):
    return [reason.code for reason in result.reasons]


class CleanScriptTest(unittest.TestCase):
    def test_clean_script_is_not_flagged_and_not_approved(self):
        script = generate_script(StubScriptGenerator(), IDEA)

        result = review_script(script, IDEA, RULES)

        self.assertFalse(result.flagged)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.script.status, ScriptStatus.DRAFT)

    def test_review_never_changes_the_original_script(self):
        script = script_with(intro="")

        review_script(script, IDEA, RULES)

        self.assertEqual(script.status, ScriptStatus.DRAFT)


class MissingPartsTest(unittest.TestCase):
    def test_incomplete_script_is_flagged_with_the_missing_parts(self):
        result = review_script(script_with(intro="", conclusion=" "), IDEA, RULES)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertEqual(codes(result), [FlagCode.MISSING_PARTS])
        self.assertIn("intro", result.reasons[0].detail)
        self.assertIn("conclusion", result.reasons[0].detail)

    def test_completely_empty_script_is_flagged_not_dropped(self):
        empty = Script(id="s", idea_id=IDEA.id, title=IDEA.title, theme=IDEA.theme)

        result = review_script(empty, IDEA, RULES)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)


class BlocklistTest(unittest.TestCase):
    def test_blocked_word_in_script_text_flags_it(self):
        result = review_script(script_with(intro="Let us mock them."), IDEA, RULES)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertEqual(codes(result), [FlagCode.BLOCKED_WORD])
        self.assertIn("mock", result.reasons[0].detail)

    def test_blocked_word_in_idea_title_flags_it(self):
        bad_idea = make_idea("A video to ridicule others", "Prophets")

        result = review_script(script_with(idea_id=bad_idea.id), bad_idea, RULES)

        self.assertIn(FlagCode.BLOCKED_WORD, codes(result))

    def test_blocked_word_in_idea_theme_flags_it(self):
        bad_idea = make_idea("A calm talk", "Terror")

        result = review_script(script_with(idea_id=bad_idea.id), bad_idea, RULES)

        self.assertIn(FlagCode.BLOCKED_WORD, codes(result))

    def test_blocklist_ignores_case_and_matches_word_starts_only(self):
        loud = review_script(script_with(intro="MOCKING is wrong."), IDEA, RULES)
        harmless = review_script(script_with(intro="Learn a new skill."), IDEA, RULES)

        self.assertIn(FlagCode.BLOCKED_WORD, codes(loud))
        self.assertFalse(harmless.flagged)


class QuranPatternTest(unittest.TestCase):
    def test_each_quran_pattern_flags_the_script(self):
        for text in (
            "In Surah Al-Baqarah we read",
            "This ayah teaches patience",
            "Look at verse 5 here",
            "See 2:255 for more",
            "Allah says that patience is good",
        ):
            with self.subTest(text=text):
                result = review_script(script_with(intro=text), IDEA, RULES)
                self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
                self.assertIn(FlagCode.POSSIBLE_QURAN, codes(result))

    def test_quran_patterns_ignore_case(self):
        result = review_script(script_with(intro="Read SURAH Yusuf."), IDEA, RULES)

        self.assertIn(FlagCode.POSSIBLE_QURAN, codes(result))

    def test_quran_patterns_are_not_applied_to_the_idea_title(self):
        verse_idea = make_idea("Every verse explained", "Quran")

        result = review_script(script_with(idea_id=verse_idea.id), verse_idea, RULES)

        self.assertNotIn(FlagCode.POSSIBLE_QURAN, codes(result))


class HadithPatternTest(unittest.TestCase):
    def test_each_hadith_pattern_flags_the_script(self):
        for text in (
            "There is a hadith about this",
            "It was narrated by Abu Hurairah",
            "This is reported by Bukhari",
            "Found in Sahih Muslim",
            "The Prophet said to be kind",
            "The Prophet (PBUH) said to be kind",
            "A sunan collection",
        ):
            with self.subTest(text=text):
                result = review_script(script_with(intro=text), IDEA, RULES)
                self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
                self.assertIn(FlagCode.POSSIBLE_HADITH, codes(result))

    def test_hadith_patterns_ignore_case(self):
        result = review_script(script_with(intro="See BUKHARI."), IDEA, RULES)

        self.assertIn(FlagCode.POSSIBLE_HADITH, codes(result))

    def test_bare_muslim_does_not_flag_the_script(self):
        text = "Every Muslim family can learn this. Muslims everywhere benefit."

        result = review_script(script_with(intro=text), IDEA, RULES)

        self.assertFalse(result.flagged)


class QuotationAndArabicTest(unittest.TestCase):
    def test_long_quotation_is_flagged(self):
        result = review_script(
            script_with(intro='He said "be patient and trust in God" often.'), IDEA, RULES)

        self.assertIn(FlagCode.POSSIBLE_QUOTATION, codes(result))

    def test_curly_quotes_are_also_checked(self):
        result = review_script(
            script_with(intro="He said “be patient and trust in God” often."),
            IDEA, RULES)

        self.assertIn(FlagCode.POSSIBLE_QUOTATION, codes(result))

    def test_short_quotation_is_not_flagged(self):
        result = review_script(script_with(intro='The word "patience" matters.'), IDEA, RULES)

        self.assertFalse(result.flagged)

    def test_arabic_script_is_flagged(self):
        result = review_script(script_with(intro="Say بسم الله"),
                               IDEA, RULES)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertIn(FlagCode.POSSIBLE_ARABIC, codes(result))


class ReasonsTest(unittest.TestCase):
    def test_every_cause_gets_its_own_stored_reason(self):
        script = script_with(
            intro="",
            sections=("Mock them. Surah Yusuf is a hadith.",),
        )

        result = review_script(script, IDEA, RULES)

        self.assertEqual(
            codes(result),
            [FlagCode.MISSING_PARTS, FlagCode.BLOCKED_WORD,
             FlagCode.POSSIBLE_QURAN, FlagCode.POSSIBLE_HADITH],
        )
        self.assertTrue(all(reason.detail for reason in result.reasons))

    def test_review_never_approves(self):
        for script in (script_with(), script_with(intro=""), script_with(intro="Surah Yusuf")):
            with self.subTest(intro=script.intro):
                result = review_script(script, IDEA, RULES)
                self.assertNotEqual(result.script.status, ScriptStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()

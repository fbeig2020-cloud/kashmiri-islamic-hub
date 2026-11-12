import tempfile
import unittest
from pathlib import Path

from src.ideas.model import Idea, IdeaStatus
from src.ideas.moderation import Rules, Verdict, apply_moderation, load_rules, moderate

# Fixed test rules, so editing the real rules file never breaks these tests.
RULES = Rules(allowed_themes=("prophets", "ramadan"), blocked_terms=("mock", "kill"))


class ModerationTest(unittest.TestCase):
    def test_allowed_idea_passes_but_is_not_approved(self):
        idea = Idea(id="1", title="The patience of Prophet Ayyub", theme="Prophets")

        result = moderate(idea, RULES)

        self.assertEqual(result.verdict, Verdict.ALLOWED)
        self.assertEqual(idea.status, IdeaStatus.PENDING)  # still waits for a human

    def test_blocked_idea_is_blocked(self):
        idea = Idea(id="2", title="Mocking the fasting people", theme="Ramadan")

        result = moderate(idea, RULES)

        self.assertEqual(result.verdict, Verdict.BLOCKED)

    def test_blocklist_beats_allowlist_and_ignores_case(self):
        idea = Idea(id="3", title="KILLING time before Iftar", theme="RAMADAN")

        self.assertEqual(moderate(idea, RULES).verdict, Verdict.BLOCKED)

    def test_blocked_term_inside_another_word_is_not_a_hit(self):
        idea = Idea(id="4", title="Building a skill for daily dua", theme="Prophets")

        self.assertEqual(moderate(idea, RULES).verdict, Verdict.ALLOWED)

    def test_uncertain_idea_is_flagged_for_review(self):
        idea = Idea(id="5", title="Cooking shows for the weekend", theme="Cooking")

        result = moderate(idea, RULES)

        self.assertEqual(result.verdict, Verdict.NEEDS_REVIEW)

    def test_missing_rules_file_raises_instead_of_allowing(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                load_rules(Path(d) / "nope.json")

    def test_real_rules_block_actor_portraying_a_prophet(self):
        idea = Idea(id="6", title="Actor portraying Prophet Yusuf", theme="Prophets")

        result = moderate(idea, load_rules())  # uses the real rules file

        self.assertEqual(result.verdict, Verdict.BLOCKED)

    def test_real_rules_file_loads_and_is_not_empty(self):
        rules = load_rules()

        self.assertTrue(rules.allowed_themes)
        self.assertTrue(rules.blocked_terms)


class ApplyModerationTest(unittest.TestCase):
    def test_allowed_idea_stays_pending(self):
        idea = Idea(id="1", title="The patience of Prophet Ayyub", theme="Prophets")

        moderated, _ = apply_moderation(idea, RULES)

        self.assertEqual(moderated.status, IdeaStatus.PENDING)

    def test_blocked_idea_becomes_removed(self):
        idea = Idea(id="2", title="Mocking the fasting people", theme="Ramadan")

        moderated, result = apply_moderation(idea, RULES)

        self.assertEqual(moderated.status, IdeaStatus.REMOVED)
        self.assertEqual(result.verdict, Verdict.BLOCKED)

    def test_uncertain_idea_becomes_flagged(self):
        idea = Idea(id="3", title="Cooking shows for the weekend", theme="Cooking")

        moderated, _ = apply_moderation(idea, RULES)

        self.assertEqual(moderated.status, IdeaStatus.FLAGGED)

    def test_original_idea_is_not_changed(self):
        idea = Idea(id="4", title="Mocking the fasting people", theme="Ramadan")

        apply_moderation(idea, RULES)

        self.assertEqual(idea.status, IdeaStatus.PENDING)

    def test_moderation_never_produces_approved(self):
        ideas = [
            Idea(id="a", title="The patience of Prophet Ayyub", theme="Prophets"),
            Idea(id="b", title="Mocking the fasting people", theme="Ramadan"),
            Idea(id="c", title="Cooking shows", theme="Cooking"),
            Idea(id="d", title="", theme=""),
        ]

        for idea in ideas:
            moderated, _ = apply_moderation(idea, RULES)
            self.assertNotEqual(moderated.status, IdeaStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()

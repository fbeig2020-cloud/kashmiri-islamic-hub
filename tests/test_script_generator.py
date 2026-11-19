import unittest

from src.ideas.generator import make_idea
from src.scripts.generator import (
    ScriptGenerationError,
    StubScriptGenerator,
    generate_script,
    make_script_id,
)
from src.scripts.model import Script, ScriptStatus

IDEA = make_idea("The patience of Prophet Ayyub", "Prophets")


class FakeGenerator:
    """Returns whatever script it was given, for failure-path tests."""

    def __init__(self, script):
        self.script = script

    def generate(self, idea):
        return self.script


class StubScriptGeneratorTest(unittest.TestCase):
    def test_stub_generates_a_complete_draft_script_for_the_idea(self):
        script = generate_script(StubScriptGenerator(), IDEA)

        self.assertEqual(script.idea_id, IDEA.id)
        self.assertEqual(script.title, IDEA.title)
        self.assertEqual(script.theme, IDEA.theme)
        self.assertEqual(script.status, ScriptStatus.DRAFT)
        self.assertTrue(script.is_complete)

    def test_same_idea_always_gives_the_same_script(self):
        first = generate_script(StubScriptGenerator(), IDEA)
        second = generate_script(StubScriptGenerator(), IDEA)

        self.assertEqual(first, second)
        self.assertEqual(first.id, make_script_id(IDEA.id))

    def test_different_ideas_get_different_script_ids(self):
        other = make_idea("Everyday duas every child can learn", "Dua")

        self.assertNotEqual(make_script_id(IDEA.id), make_script_id(other.id))

    def test_stub_says_it_is_not_real_ai(self):
        script = generate_script(StubScriptGenerator(), IDEA)

        self.assertIn("Stub draft", script.intro)


class GenerateScriptFailureTest(unittest.TestCase):
    def test_none_raises_instead_of_returning_nothing(self):
        with self.assertRaises(ScriptGenerationError):
            generate_script(FakeGenerator(None), IDEA)

    def test_completely_empty_script_raises(self):
        empty = Script(id="s", idea_id=IDEA.id, title="T", theme="Prophets")

        with self.assertRaises(ScriptGenerationError):
            generate_script(FakeGenerator(empty), IDEA)

    def test_script_for_a_different_idea_raises(self):
        wrong = Script(
            id="s", idea_id="idea-other", title="T", theme="Prophets",
            intro="i", sections=("s",), conclusion="c",
        )

        with self.assertRaises(ScriptGenerationError):
            generate_script(FakeGenerator(wrong), IDEA)

    def test_partly_filled_script_is_returned_for_review_not_rejected(self):
        partial = Script(
            id="s", idea_id=IDEA.id, title="T", theme="Prophets",
            intro="Only an intro.",
        )

        script = generate_script(FakeGenerator(partial), IDEA)

        self.assertEqual(script, partial)
        self.assertFalse(script.is_complete)


if __name__ == "__main__":
    unittest.main()

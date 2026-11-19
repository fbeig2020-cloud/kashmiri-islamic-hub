import unittest

from src.scripts.model import Script, ScriptStatus


def full_script(**changes):
    fields = dict(
        id="script-1",
        idea_id="idea-1",
        title="The patience of Prophet Ayyub",
        theme="Prophets",
        intro="Welcome. Today we look at patience.",
        sections=("Who Ayyub was.", "How he stayed patient."),
        conclusion="Thank you for watching.",
    )
    fields.update(changes)
    return Script(**fields)


class ScriptModelTest(unittest.TestCase):
    def test_script_can_be_created_and_starts_as_draft(self):
        script = full_script()

        self.assertEqual(script.idea_id, "idea-1")
        self.assertEqual(script.status, ScriptStatus.DRAFT)
        self.assertEqual(len(script.sections), 2)

    def test_complete_script_has_no_missing_parts(self):
        script = full_script()

        self.assertEqual(script.missing_parts(), ())
        self.assertTrue(script.is_complete)

    def test_empty_script_is_incomplete(self):
        script = Script(id="s", idea_id="i", title="T", theme="Quran")

        self.assertEqual(script.missing_parts(), ("intro", "sections", "conclusion"))
        self.assertFalse(script.is_complete)

    def test_blank_parts_count_as_missing(self):
        script = full_script(intro="   ", conclusion="\n")

        self.assertEqual(script.missing_parts(), ("intro", "conclusion"))

    def test_blank_section_is_reported(self):
        script = full_script(sections=("Real section.", "  "))

        self.assertEqual(script.missing_parts(), ("blank section",))
        self.assertFalse(script.is_complete)

    def test_script_is_immutable(self):
        script = full_script()

        with self.assertRaises(Exception):
            script.status = ScriptStatus.APPROVED


if __name__ == "__main__":
    unittest.main()

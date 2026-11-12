import tempfile
import unittest
from pathlib import Path

from src.ideas.generator import NoIdeasError, StubIdeaGenerator, make_idea
from src.ideas.log import IdeaLog
from src.ideas.model import IdeaStatus
from src.ideas.moderation import Rules
from src.ideas.pipeline import run_pipeline

RULES = Rules(allowed_themes=("prophets", "ramadan"), blocked_terms=("mock",))


class FixedGenerator:
    def __init__(self, ideas):
        self._ideas = ideas

    def generate(self, prompt):
        return list(self._ideas)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "data" / "ideas.jsonl"  # never the real data/
        self.log = IdeaLog(self.path)

    def _logged(self):
        return [(e["idea"]["id"], e["idea"]["status"]) for e in self.log.read()]

    def test_stub_ideas_are_returned_and_every_one_is_logged(self):
        visible = run_pipeline(StubIdeaGenerator(), "any prompt", self.log)  # real rules file

        self.assertGreater(len(visible), 0)
        logged_ids = {e["idea"]["id"] for e in self.log.read()}
        self.assertEqual(logged_ids, {i.id for i in StubIdeaGenerator().generate("")})
        self.assertNotIn(IdeaStatus.APPROVED, {i.status for i in visible})

    def test_inappropriate_idea_is_hidden_but_logged_as_removed(self):
        good = make_idea("The patience of Prophet Ayyub", "Prophets")
        bad = make_idea("Mocking the fasting people", "Ramadan")

        visible = run_pipeline(FixedGenerator([good, bad]), "p", self.log, RULES)

        self.assertEqual([i.id for i in visible], [good.id])
        self.assertIn((bad.id, "removed"), self._logged())
        self.assertIn((bad.id, "pending"), self._logged())  # logged before moderating

    def test_uncertain_idea_stays_visible_as_flagged_and_is_logged(self):
        odd = make_idea("Cooking shows", "Cooking")

        visible = run_pipeline(FixedGenerator([odd]), "p", self.log, RULES)

        self.assertEqual([(i.id, i.status) for i in visible], [(odd.id, IdeaStatus.FLAGGED)])
        self.assertIn((odd.id, "flagged"), self._logged())

    def test_running_twice_does_not_duplicate_log_lines(self):
        gen = FixedGenerator(
            [
                make_idea("The patience of Prophet Ayyub", "Prophets"),
                make_idea("Mocking the fasting people", "Ramadan"),
                make_idea("Cooking shows", "Cooking"),
            ]
        )

        first = run_pipeline(gen, "p", self.log, RULES)
        lines_after_first = len(self.log.read())
        second = run_pipeline(gen, "p", self.log, RULES)

        self.assertEqual(len(self.log.read()), lines_after_first)
        self.assertEqual(first, second)

    def test_generator_returning_nothing_raises_and_logs_nothing(self):
        with self.assertRaises(NoIdeasError):
            run_pipeline(FixedGenerator([]), "p", self.log, RULES)

        self.assertEqual(self.log.read(), [])


if __name__ == "__main__":
    unittest.main()

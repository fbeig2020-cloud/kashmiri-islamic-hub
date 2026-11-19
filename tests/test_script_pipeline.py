import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.ideas.generator import StubIdeaGenerator, make_idea
from src.ideas.model import IdeaStatus
from src.scripts.generator import ScriptGenerationError, StubScriptGenerator
from src.scripts.log import ScriptLog, ScriptSaveError
from src.scripts.model import Script, ScriptStatus
from src.scripts.pipeline import IdeaNotEligibleError, run_script_pipeline

CLEAN_IDEA = make_idea("The patience of Prophet Ayyub", "Prophets")
HADITH_IDEA = make_idea("The story behind a well-known hadith on kindness", "Hadith")


class FakeGenerator:
    """Returns a script built by `build(idea)`, and counts its calls."""

    def __init__(self, build):
        self.build = build
        self.calls = 0

    def generate(self, idea):
        self.calls += 1
        return self.build(idea)


def script_for(idea, **changes):
    fields = dict(
        id="script-fake", idea_id=idea.id, title=idea.title, theme=idea.theme,
        intro="Welcome.", sections=("Point one.",), conclusion="Thanks.",
    )
    fields.update(changes)
    return Script(**fields)


class FailsOnNthSave(ScriptLog):
    def __init__(self, path, fail_on):
        super().__init__(path)
        self.fail_on = fail_on
        self.saves = 0

    def append(self, script, reasons=(), now=None):
        self.saves += 1
        if self.saves == self.fail_on:
            raise ScriptSaveError("disk full")
        return super().append(script, reasons, now)


class ScriptPipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "data" / "scripts.jsonl"  # never the real data/
        self.log = ScriptLog(self.path)

    def statuses(self):
        return [e["script"]["status"] for e in self.log.read()]

    # happy path

    def test_idea_gives_a_logged_draft_script(self):
        result = run_script_pipeline(StubScriptGenerator(), CLEAN_IDEA, self.log)

        self.assertEqual(result.script.idea_id, CLEAN_IDEA.id)
        self.assertEqual(result.script.status, ScriptStatus.DRAFT)
        self.assertEqual(result.reasons, ())
        self.assertEqual(self.statuses(), ["draft"])

    # flagged paths

    def test_script_that_quotes_a_hadith_is_flagged_and_the_reason_logged(self):
        result = run_script_pipeline(StubScriptGenerator(), HADITH_IDEA, self.log)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        entries = self.log.read()
        self.assertEqual([e["script"]["status"] for e in entries], ["draft", "flagged"])
        self.assertEqual(entries[0]["reasons"], [])
        self.assertEqual([r["code"] for r in entries[1]["reasons"]], ["possible_hadith"])

    def test_incomplete_script_is_flagged_for_human_completion(self):
        generator = FakeGenerator(lambda idea: script_for(idea, conclusion="", sections=()))

        result = run_script_pipeline(generator, CLEAN_IDEA, self.log)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertEqual(self.statuses(), ["draft", "flagged"])
        self.assertEqual(self.log.read()[1]["reasons"][0]["code"], "missing_parts")

    def test_inappropriate_content_is_flagged_not_dropped(self):
        generator = FakeGenerator(lambda idea: script_for(idea, intro="Let us ridicule them."))

        result = run_script_pipeline(generator, CLEAN_IDEA, self.log)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertEqual(self.log.read()[1]["reasons"][0]["code"], "blocked_word")

    # idempotency

    def test_running_twice_adds_nothing_the_second_time(self):
        for idea in (CLEAN_IDEA, HADITH_IDEA):
            run_script_pipeline(StubScriptGenerator(), idea, self.log)
        before = self.path.read_text(encoding="utf-8")

        for idea in (CLEAN_IDEA, HADITH_IDEA):
            run_script_pipeline(StubScriptGenerator(), idea, self.log)

        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertEqual(len(before.splitlines()), 3)  # clean draft + hadith draft + flag

    # failure paths

    def test_removed_idea_gets_no_script_and_nothing_is_logged(self):
        removed = replace(CLEAN_IDEA, status=IdeaStatus.REMOVED)
        generator = FakeGenerator(lambda idea: script_for(idea))

        with self.assertRaises(IdeaNotEligibleError):
            run_script_pipeline(generator, removed, self.log)

        self.assertEqual(generator.calls, 0)
        self.assertEqual(self.log.read(), [])

    def test_failing_generator_raises_and_nothing_is_logged(self):
        generator = FakeGenerator(lambda idea: None)

        with self.assertRaises(ScriptGenerationError):
            run_script_pipeline(generator, CLEAN_IDEA, self.log)

        self.assertEqual(self.log.read(), [])

    def test_failing_save_of_the_draft_raises_and_no_result_is_returned(self):
        log = FailsOnNthSave(self.path, fail_on=1)

        with self.assertRaises(ScriptSaveError):
            run_script_pipeline(StubScriptGenerator(), CLEAN_IDEA, log)

        self.assertEqual(log.read(), [])

    def test_failing_save_of_the_flag_raises_and_a_rerun_completes_it(self):
        log = FailsOnNthSave(self.path, fail_on=2)

        with self.assertRaises(ScriptSaveError):
            run_script_pipeline(StubScriptGenerator(), HADITH_IDEA, log)
        self.assertEqual([e["script"]["status"] for e in log.read()], ["draft"])  # not lost

        result = run_script_pipeline(StubScriptGenerator(), HADITH_IDEA, log)  # retry

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertEqual([e["script"]["status"] for e in log.read()], ["draft", "flagged"])

    # guardrail: a human approves, never this code

    def test_pre_approved_script_is_flagged_with_the_reason_logged(self):
        generator = FakeGenerator(lambda idea: script_for(idea, status=ScriptStatus.APPROVED))

        result = run_script_pipeline(generator, CLEAN_IDEA, self.log)

        self.assertEqual(result.script.status, ScriptStatus.FLAGGED)
        self.assertEqual([r.code.value for r in result.reasons], ["pre_approved"])
        entries = self.log.read()
        self.assertEqual([e["script"]["status"] for e in entries], ["draft", "flagged"])
        self.assertEqual(entries[1]["reasons"], [
            {"code": "pre_approved", "detail": "generator returned a pre-approved script"}])

    def test_pre_approved_reason_comes_first_and_keeps_the_other_reasons(self):
        generator = FakeGenerator(lambda idea: script_for(
            idea, status=ScriptStatus.APPROVED, intro="Let us mock them."))

        result = run_script_pipeline(generator, CLEAN_IDEA, self.log)

        self.assertEqual([r.code.value for r in result.reasons], ["pre_approved", "blocked_word"])
        self.assertEqual(
            [r["code"] for r in self.log.read()[1]["reasons"]], ["pre_approved", "blocked_word"])

    def test_pipeline_never_produces_an_approved_status(self):
        ideas = StubIdeaGenerator().generate("any prompt")
        ideas += [replace(CLEAN_IDEA, status=IdeaStatus.APPROVED)]
        builders = {
            "stub": StubScriptGenerator(),
            "incomplete": FakeGenerator(lambda i: script_for(i, intro="")),
            "blocked": FakeGenerator(lambda i: script_for(i, intro="mock them")),
            "claims approved": FakeGenerator(
                lambda i: script_for(i, status=ScriptStatus.APPROVED)),
        }

        for name, generator in builders.items():
            log = ScriptLog(Path(self._tmp.name) / name / "scripts.jsonl")
            for idea in ideas:
                with self.subTest(generator=name, idea=idea.id):
                    result = run_script_pipeline(generator, idea, log)
                    self.assertIn(result.script.status, (ScriptStatus.DRAFT, ScriptStatus.FLAGGED))
            logged = {e["script"]["status"] for e in log.read()}
            self.assertTrue(logged <= {"draft", "flagged"}, f"{name}: logged {logged}")
            self.assertNotIn("approved", logged)


if __name__ == "__main__":
    unittest.main()

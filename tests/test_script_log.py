import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from src.ideas.generator import make_idea
from src.ideas.moderation import load_rules
from src.scripts.log import ScriptLog, ScriptSaveError
from src.scripts.model import Script, ScriptStatus
from src.scripts.review import FlagCode, FlagReason, review_script

IDEA = make_idea("The patience of Prophet Ayyub", "Prophets")


def a_script(**changes):
    fields = dict(
        id="script-a",
        idea_id=IDEA.id,
        title=IDEA.title,
        theme=IDEA.theme,
        intro="Welcome.",
        sections=("Who Ayyub was.", "How he stayed patient."),
        conclusion="Thank you.",
    )
    fields.update(changes)
    return Script(**fields)


class ScriptLogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "data" / "scripts.jsonl"  # never the real data/
        self.log = ScriptLog(self.path)

    def lines(self):
        return self.path.read_text(encoding="utf-8").splitlines()

    # (a) idempotency

    def test_saving_the_same_script_id_and_status_twice_writes_one_line(self):
        script = a_script()

        self.assertTrue(self.log.append(script))
        self.assertFalse(self.log.append(script))

        self.assertEqual(len(self.lines()), 1)

    def test_status_change_is_a_new_line_and_history_is_kept(self):
        script = a_script()

        self.log.append(script)
        self.log.append(replace(script, status=ScriptStatus.FLAGGED))

        statuses = [e["script"]["status"] for e in self.log.read()]
        self.assertEqual(statuses, ["draft", "flagged"])

    def test_logged_script_can_be_read_back_in_full(self):
        script = a_script()

        self.log.append(script)
        entry = self.log.read()[0]

        self.assertEqual(entry["script"]["id"], "script-a")
        self.assertEqual(entry["script"]["idea_id"], IDEA.id)
        self.assertEqual(entry["script"]["intro"], "Welcome.")
        self.assertEqual(entry["script"]["sections"], ["Who Ayyub was.", "How he stayed patient."])
        self.assertEqual(entry["script"]["conclusion"], "Thank you.")
        self.assertEqual(entry["script"]["status"], "draft")
        self.assertEqual(entry["reasons"], [])
        self.assertIn("logged_at", entry)

    def test_arabic_text_round_trips(self):
        script = a_script(intro="بسم الله")

        self.log.append(script)

        self.assertEqual(self.log.read()[0]["script"]["intro"], script.intro)

    # (b) a failing save raises and the script is not treated as saved

    def test_failing_save_raises_an_explicit_error_and_nothing_is_saved(self):
        blocker = self.dir / "data"
        blocker.write_text("not a folder")  # data/ cannot be created: a file is in the way
        script = a_script()

        with self.assertRaises(ScriptSaveError) as caught:
            self.log.append(script)

        self.assertIn("script-a", str(caught.exception))
        self.assertEqual(self.log.read(), [])

    def test_failing_write_raises_and_a_retry_after_the_fault_still_saves(self):
        script = a_script()

        with mock.patch("builtins.open", side_effect=PermissionError("disk is read-only")):
            with self.assertRaises(ScriptSaveError):
                self.log.append(script)
        self.assertEqual(self.log.read(), [])

        self.assertTrue(self.log.append(script))  # not wrongly remembered as saved
        self.assertEqual(len(self.lines()), 1)

    def test_corrupt_log_makes_the_save_fail_loudly(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'{"key": "x"}\nnot json\n')

        with self.assertRaises(ScriptSaveError):
            self.log.append(a_script())

    def test_save_error_is_not_swallowed_into_a_false_return(self):
        blocker = self.dir / "data"
        blocker.write_text("not a folder")

        try:
            result = self.log.append(a_script())
        except ScriptSaveError:
            result = "raised"

        self.assertEqual(result, "raised")

    # (c) flag reasons are stored with each flagged entry

    def test_flag_reasons_are_stored_with_a_flagged_entry(self):
        reasons = (
            FlagReason(FlagCode.POSSIBLE_QURAN, "possible Quran verse: 'surah'"),
            FlagReason(FlagCode.BLOCKED_WORD, "blocked word: 'mock'"),
        )
        flagged = a_script(status=ScriptStatus.FLAGGED)

        self.log.append(flagged, reasons)
        entry = self.log.read()[0]

        self.assertEqual(entry["script"]["status"], "flagged")
        self.assertEqual(entry["reasons"], [
            {"code": "possible_quran", "detail": "possible Quran verse: 'surah'"},
            {"code": "blocked_word", "detail": "blocked word: 'mock'"},
        ])

    def test_reasons_from_a_real_review_are_stored(self):
        script = a_script(intro="", sections=("See Surah Yusuf.",))
        result = review_script(script, IDEA, load_rules())

        self.log.append(result.script, result.reasons)
        entry = self.log.read()[0]

        self.assertEqual(entry["script"]["status"], "flagged")
        self.assertEqual([r["code"] for r in entry["reasons"]],
                         ["missing_parts", "possible_quran"])

    # crash safety, as in the idea log

    def test_truncated_last_line_is_skipped_and_cleaned_up_on_next_save(self):
        self.log.append(a_script())
        with open(self.path, "ab") as f:  # simulate a crash mid-write
            f.write(b'{"key": "script-b:draft", "logged_at": "2026-')

        self.assertEqual([e["script"]["id"] for e in self.log.read()], ["script-a"])

        self.assertTrue(self.log.append(a_script(id="script-c")))
        self.assertEqual([e["script"]["id"] for e in self.log.read()], ["script-a", "script-c"])


class DataFolderIsIgnoredTest(unittest.TestCase):
    def test_gitignore_keeps_data_out_of_git(self):
        root = Path(__file__).resolve().parent.parent
        ignored = (root / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertIn("data/", [line.strip() for line in ignored])


if __name__ == "__main__":
    unittest.main()

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.ideas.generator import make_idea
from src.scripts.generator import StubScriptGenerator, make_script_id
from src.scripts.log import ScriptLog
from src.scripts.pipeline import run_script_pipeline

ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = ROOT / "scripts" / "review_scripts.py"
_spec = importlib.util.spec_from_file_location("review_cli", CLI_PATH)
cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cli)

IDEA = make_idea("The story behind a well-known hadith on kindness", "Hadith")
SCRIPT_ID = make_script_id(IDEA.id)


class ArabicStub:
    def generate(self, idea):
        script = StubScriptGenerator().generate(idea)
        return replace(script, sections=("Say بسم الله", "Hidden\x1b[2Ktext\rhere"))


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data = Path(self._tmp.name) / "data"  # never the real data/
        self.actions = self.data / "review_actions.jsonl"

    def add_script(self, generator=None):
        return run_script_pipeline(
            generator or StubScriptGenerator(), IDEA, ScriptLog(self.data / "scripts.jsonl"))

    def run_cli(self, *args):
        """(exit code, stdout, stderr)"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["--data-dir", str(self.data), *args])
        return code, out.getvalue(), err.getvalue()


class ListTest(CliTestCase):
    def test_list_shows_the_full_text_and_the_reasons(self):
        result = self.add_script(ArabicStub())

        code, out, _ = self.run_cli("list")

        self.assertEqual(code, 0)
        script = result.script
        for text in (SCRIPT_ID, "[pending]", script.title, script.theme, script.intro,
                     "Say بسم الله", script.conclusion):
            self.assertIn(text, out)
        for reason in result.reasons:
            self.assertIn(f"[{reason.code.value}] {reason.detail}", out)

    def test_control_characters_are_shown_not_obeyed(self):
        self.add_script(ArabicStub())

        _, out, _ = self.run_cli("list")

        self.assertNotIn("\x1b", out)
        self.assertNotIn("\r", out)
        self.assertIn("Hidden\\x1b[2Ktext\\rhere", out)

    def test_decided_scripts_are_listed_only_with_all(self):
        self.add_script()
        self.run_cli("reject", SCRIPT_ID, "--reviewer", "Aisha", "--note", "wrong source")

        _, pending, _ = self.run_cli("list")
        _, everything, _ = self.run_cli("list", "--all")

        self.assertIn("0 pending flagged script(s)", pending)
        self.assertNotIn(SCRIPT_ID, pending)
        for text in (SCRIPT_ID, "[rejected]", "rejected by Aisha", "wrong source"):
            self.assertIn(text, everything)

    def test_unreadable_log_gives_an_error_not_an_empty_list(self):
        self.data.mkdir(parents=True)
        (self.data / "scripts.jsonl").write_bytes(b"not json\n")

        code, out, err = self.run_cli("list")

        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("Could not read the script log", err)


class DecideTest(CliTestCase):
    def test_approve_and_reject_print_a_receipt(self):
        for command, decision in (("approve", "approved"), ("reject", "rejected")):
            with self.subTest(command=command):
                self.data = Path(self._tmp.name) / command
                result = self.add_script()

                code, out, err = self.run_cli(command, SCRIPT_ID, "--reviewer", "  Aisha ")

                self.assertEqual((code, err), (0, ""))
                for text in ("Decision saved.", SCRIPT_ID, result.script.title, decision,
                             "Reviewer:   Aisha\n", "[possible_hadith]",
                             result.reasons[0].detail):
                    self.assertIn(text, out)

    def test_identical_repeat_says_nothing_changed(self):
        self.add_script()
        self.run_cli("approve", SCRIPT_ID, "--reviewer", "Aisha")
        before = (self.data / "review_actions.jsonl").read_bytes()

        code, out, err = self.run_cli("approve", SCRIPT_ID, "--reviewer", "Aisha ")

        self.assertEqual((code, out, err), (0, "already decided, nothing changed\n", ""))
        self.assertEqual((self.data / "review_actions.jsonl").read_bytes(), before)

    def test_conflicting_decision_names_who_decided(self):
        self.add_script()
        self.run_cli("approve", SCRIPT_ID, "--reviewer", "Aisha")

        code, out, err = self.run_cli("reject", SCRIPT_ID, "--reviewer", "Bilal")

        self.assertEqual((code, out), (1, ""))
        self.assertIn("already approved by 'Aisha'", err)

    def test_refused_decisions_save_nothing(self):
        self.add_script()
        for script_id, reviewer, message in (
            ("script-nope", "Aisha", "There is no script"),
            (SCRIPT_ID, "   ", "reviewer name is required"),
        ):
            with self.subTest(message=message):
                code, out, err = self.run_cli("approve", script_id, "--reviewer", reviewer)

                self.assertEqual((code, out), (1, ""))
                self.assertIn(message, err)
        self.assertFalse(self.actions.exists())

    def test_failed_save_prints_an_error_and_no_receipt(self):
        self.add_script()
        self.actions.mkdir()  # a folder where the file should be

        code, out, err = self.run_cli("approve", SCRIPT_ID, "--reviewer", "Aisha")

        self.assertEqual((code, out), (1, ""))
        self.assertTrue(err.startswith("Error: "))


class RealProcessTest(CliTestCase):
    def run_process(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="cp1252")  # a typical Windows default
        return subprocess.run(
            [sys.executable, str(CLI_PATH), "--data-dir", str(self.data), *args],
            capture_output=True, env=env, cwd=self._tmp.name, timeout=60)

    def test_arabic_prints_and_errors_have_no_traceback(self):
        self.add_script(ArabicStub())

        listed = self.run_process("list")
        refused = self.run_process("approve", "script-nope", "--reviewer", "Aisha")

        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("بسم الله", listed.stdout.decode("utf-8"))
        self.assertEqual(refused.returncode, 1)
        self.assertNotIn(b"Traceback", refused.stderr)

    def test_default_folder_is_the_repo_data_folder(self):
        # Checked without running it, so the real data/ is never touched.
        self.assertEqual(cli.parse_args(["list"]).data_dir, ROOT / "data")


if __name__ == "__main__":
    unittest.main()

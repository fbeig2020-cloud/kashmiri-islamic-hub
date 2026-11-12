import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.ideas.log import IdeaLog
from src.ideas.model import Idea, IdeaStatus


class IdeaLogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "data" / "ideas.jsonl"  # never the real data/
        self.log = IdeaLog(self.path)

    def test_logged_ideas_can_be_read_back(self):
        a = Idea(id="idea-a", title="The patience of Prophet Ayyub", theme="Prophets")
        b = Idea(id="idea-b", title="Simple ways to make the most of Ramadan", theme="Ramadan")

        self.assertTrue(self.log.append(a))
        self.assertTrue(self.log.append(b))
        entries = self.log.read()

        self.assertEqual([e["idea"]["id"] for e in entries], ["idea-a", "idea-b"])
        self.assertEqual(entries[0]["idea"]["title"], a.title)
        self.assertEqual(entries[0]["idea"]["theme"], "Prophets")
        self.assertEqual(entries[0]["idea"]["status"], "pending")
        self.assertIn("logged_at", entries[0])
        self.assertIn("key", entries[0])

    def test_logging_the_same_idea_twice_gives_one_line(self):
        idea = Idea(id="idea-a", title="T", theme="Dua")

        self.assertTrue(self.log.append(idea))
        self.assertFalse(self.log.append(idea))

        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 1)

    def test_status_change_is_a_new_line_and_history_is_kept(self):
        idea = Idea(id="idea-a", title="T", theme="Dua")

        self.log.append(idea)
        self.log.append(replace(idea, status=IdeaStatus.REMOVED))

        statuses = [e["idea"]["status"] for e in self.log.read()]
        self.assertEqual(statuses, ["pending", "removed"])

    def test_truncated_last_line_is_skipped_when_reading(self):
        self.log.append(Idea(id="idea-a", title="T", theme="Dua"))
        with open(self.path, "ab") as f:  # simulate a crash mid-write
            f.write(b'{"key": "idea-b:pending", "logged_at": "2026-')

        entries = self.log.read()

        self.assertEqual([e["idea"]["id"] for e in entries], ["idea-a"])

    def test_append_after_a_crash_cleans_up_the_partial_line(self):
        self.log.append(Idea(id="idea-a", title="T", theme="Dua"))
        with open(self.path, "ab") as f:
            f.write(b'{"key": "idea-b:pen')

        self.log.append(Idea(id="idea-c", title="T2", theme="Hajj"))

        self.assertEqual([e["idea"]["id"] for e in self.log.read()], ["idea-a", "idea-c"])

    def test_corrupt_line_in_the_middle_raises(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'not json\n{"key": "x"}\n')

        with self.assertRaises(ValueError):
            self.log.read()

    def test_reading_a_missing_log_gives_empty_list(self):
        self.assertEqual(self.log.read(), [])


if __name__ == "__main__":
    unittest.main()

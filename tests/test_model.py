import unittest

from src.ideas.model import Idea, IdeaStatus


class IdeaModelTest(unittest.TestCase):
    def test_idea_can_be_created_and_starts_pending(self):
        idea = Idea(id="idea-1", title="The story of Prophet Yusuf", theme="Prophets")

        self.assertEqual(idea.id, "idea-1")
        self.assertEqual(idea.title, "The story of Prophet Yusuf")
        self.assertEqual(idea.theme, "Prophets")
        self.assertEqual(idea.status, IdeaStatus.PENDING)


if __name__ == "__main__":
    unittest.main()

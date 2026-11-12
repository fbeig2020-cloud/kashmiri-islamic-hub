import unittest

from src.ideas.generator import (
    NoIdeasError,
    StubIdeaGenerator,
    generate_ideas,
    make_idea_id,
)
from src.ideas.model import Idea, IdeaStatus


class EmptyGenerator:
    def generate(self, prompt):
        return []


class GeneratorTest(unittest.TestCase):
    def test_stub_returns_a_list_of_ideas(self):
        ideas = generate_ideas(StubIdeaGenerator(), "ideas about Ramadan")

        self.assertGreater(len(ideas), 0)
        for idea in ideas:
            self.assertIsInstance(idea, Idea)
            self.assertEqual(idea.status, IdeaStatus.PENDING)

    def test_generator_returning_nothing_raises_a_clear_error(self):
        with self.assertRaises(NoIdeasError) as ctx:
            generate_ideas(EmptyGenerator(), "anything")

        self.assertIn("no ideas", str(ctx.exception))

    def test_ids_are_deterministic_and_unique(self):
        first = [i.id for i in generate_ideas(StubIdeaGenerator(), "a")]
        second = [i.id for i in generate_ideas(StubIdeaGenerator(), "b")]

        self.assertEqual(first, second)  # running twice gives the same ids
        self.assertEqual(len(first), len(set(first)))  # no duplicates inside
        self.assertEqual(make_idea_id("A Title", "Dua"), make_idea_id(" a title ", "DUA"))


if __name__ == "__main__":
    unittest.main()

import unittest

from app.agent.continuity import missing_context_reply, refers_to_previous_turn, search_question, unsupported_followup_reply


class ContinuityTest(unittest.TestCase):
    def test_followup_uses_previous_topic_for_retrieval(self):
        history = [
            {"role": "user", "content": "What property qualifies for a Section 1031 exchange?"},
            {"role": "assistant", "content": "Only real property qualifies."},
        ]
        query = search_question("Can you expand on what you just said?", history)
        self.assertEqual(query, "What property qualifies for a Section 1031 exchange?")

    def test_standalone_question_remains_standalone(self):
        self.assertEqual(
            search_question("Which property qualifies for Section 1031?", []),
            "Which property qualifies for Section 1031?",
        )

    def test_no_history_asks_for_topic_instead_of_claiming_missing_source(self):
        self.assertTrue(refers_to_previous_turn("Can you expand on what you just said?"))
        self.assertIn("earlier exchange", missing_context_reply("Can you expand on what you just said?", "en"))
        self.assertIn("don't have an earlier exchange", missing_context_reply("Can you expand on what you just said?", "en", memory_enabled=True))

    def test_unsupported_reason_does_not_guess(self):
        self.assertIn("doesn't explain why", unsupported_followup_reply("Why is that excluded?", "en"))


if __name__ == "__main__":
    unittest.main()

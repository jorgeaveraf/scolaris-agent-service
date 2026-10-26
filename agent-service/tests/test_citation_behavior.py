import unittest

from app.agent.graph import grounded_followup_answer, verify_grounded_answer
from app.main import strip_source_mentions


class CitationBehaviorTest(unittest.TestCase):
    def test_source_refusal_does_not_earn_citations(self):
        state = {
            "question": "Compare the 2016 and 2025 instructions.",
            "language": "en",
            "context": [{"title": "IRS 2016", "content": "Personal properties of a like class are like-kind."}],
        }
        answer, supported = grounded_followup_answer(
            state,
            "The provided fragments do not contain enough information to compare the rules.",
            followup=False,
        )
        self.assertFalse(supported)
        self.assertIn("sufficient source", answer)

    def test_public_answer_uses_document_links_instead_of_internal_fragment_numbers(self):
        answer = strip_source_mentions(
            "The older guidance covers personal property (fragments 1, 2, and 3). "
            "The newer guidance is limited to real property (fragments 4 and 5)."
        )
        self.assertEqual(
            answer,
            "The older guidance covers personal property. "
            "The newer guidance is limited to real property.",
        )
        self.assertEqual(
            strip_source_mentions("The guidance changed (Framents 1, 2, and 3)."),
            "The guidance changed.",
        )
        self.assertEqual(
            strip_source_mentions("The rule applies to real property (excerpt 1), but excludes property held for sale (excerpt 5)."),
            "The rule applies to real property, but excludes property held for sale.",
        )

    def test_unmentioned_law_name_cannot_pass_evidence_check(self):
        state = {
            "context": [{"title": "2016 guidance", "content": "Personal properties of a like class are like-kind."}],
        }
        self.assertFalse(
            verify_grounded_answer(
                state,
                "The Tax Cuts and Jobs Act made this change.",
            )
        )


if __name__ == "__main__":
    unittest.main()

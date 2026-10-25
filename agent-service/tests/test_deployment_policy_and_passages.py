import unittest
from unittest.mock import patch

from app.agent.graph import classify_request_policy, select_supporting_passages
from app.main import _source_records


class DeploymentPolicyAndPassagesTest(unittest.TestCase):
    def test_policy_is_inactive_without_deployment_rules(self):
        with patch("app.agent.graph.policy_rules", return_value=""), patch("app.agent.graph.advice_rules", return_value=""):
            self.assertEqual(classify_request_policy("Hello", "test"), "ALLOW")

    def test_configured_policy_rejects_personalized_advice(self):
        with patch("app.agent.graph.policy_rules", return_value="1031 exchanges"), patch(
            "app.agent.graph.advice_rules", return_value="Personalized tax advice"
        ), patch("app.agent.graph._invoke_llm", side_effect=[("IN", None, None, None), ("YES", None, None, None)]):
            self.assertEqual(classify_request_policy("Should I do this exchange?", "test"), "REJECT_ADVICE")

    def test_unrelated_topic_is_rejected_before_advice_check(self):
        with patch("app.agent.graph.policy_rules", return_value="IRS like-kind exchanges"), patch(
            "app.agent.graph.advice_rules", return_value="Personalized tax advice"
        ), patch("app.agent.graph._invoke_llm", return_value=("OUT", None, None, None)) as model:
            self.assertEqual(classify_request_policy("What is the weather in Paris?", "test"), "REJECT_SCOPE")
            self.assertEqual(model.call_count, 1)

    def test_only_verified_passage_is_cited(self):
        state = {
            "request_id": "test",
            "context": [
                {"title": "Relevant", "source": "https://example.org/relevant", "content": "A qualifying exchange involves eligible real property."},
                {"title": "Other", "source": "https://example.org/other", "content": "An unrelated explanation appears here."},
            ],
        }
        answer = "A qualifying exchange involves eligible real property."
        verdict = ('{"support":[{"sentence":0,"citations":[{"index":0,"passage":"A qualifying exchange involves eligible real property."}]}]}', None, None, None)
        with patch("app.agent.graph._invoke_llm", return_value=verdict), patch(
            "app.agent.graph.verify_grounded_answer", return_value=True
        ):
            passages = select_supporting_passages(state, answer)
        self.assertEqual(len(passages), 1)
        self.assertEqual(_source_records(passages)[0]["snippet"], answer)
        self.assertEqual(_source_records(passages)[0]["url"], "https://example.org/relevant")

    def test_uncopied_passage_cannot_be_cited(self):
        state = {"request_id": "test", "context": [{"title": "Source", "content": "Actual text in the source."}]}
        verdict = ('{"support":[{"sentence":0,"citations":[{"index":0,"passage":"Fabricated passage from the source."}]}]}', None, None, None)
        with patch("app.agent.graph._invoke_llm", return_value=verdict):
            self.assertEqual(select_supporting_passages(state, "Fabricated claim"), [])

    def test_quote_punctuation_variation_uses_original_source_text(self):
        source = "Real property—used for business or held as an investment—may qualify."
        state = {"request_id": "test", "context": [{"title": "Source", "content": source}]}
        verdict = ('{"support":[{"sentence":0,"citations":[{"index":0,"passage":"Real property used for business or held as an investment may qualify"}]}]}', None, None, None)
        with patch("app.agent.graph._invoke_llm", return_value=verdict), patch(
            "app.agent.graph.verify_grounded_answer", return_value=True
        ):
            passages = select_supporting_passages(state, "Some real property may qualify.")
        self.assertEqual(passages[0]["evidence_quote"], source)

    def test_missing_sentence_support_rejects_all_citations(self):
        state = {"request_id": "test", "context": [{"title": "Source", "content": "A qualifying exchange involves eligible real property."}]}
        verdict = ('{"support":[{"sentence":0,"citations":[{"index":0,"passage":"A qualifying exchange involves eligible real property."}]}]}', None, None, None)
        with patch("app.agent.graph._invoke_llm", return_value=verdict):
            self.assertEqual(select_supporting_passages(state, "A qualifying exchange involves eligible real property. An unsupported exception also applies."), [])


if __name__ == "__main__":
    unittest.main()

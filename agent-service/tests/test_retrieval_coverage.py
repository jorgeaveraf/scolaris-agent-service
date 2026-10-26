import unittest
from unittest.mock import patch

from app.agent.graph import _complete_split_context, _diverse_named_context


class RetrievalCoverageTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"doc_id": "sightbridge", "title": "Sightbridge strategies", "score": 0.73, "content": "Sightbridge strategy one."},
            {"doc_id": "sightbridge", "title": "Sightbridge strategies", "score": 0.67, "content": "Sightbridge strategy two."},
            {"doc_id": "dst", "title": "IRS DST ruling", "score": 0.59, "content": "DST eligibility has conditions."},
            {"doc_id": "sec", "title": "SEC nontraded REITs", "score": 0.47, "content": "Redemption programs may have limits."},
        ]

    def test_named_sources_survive_a_lower_semantic_score(self):
        found = _diverse_named_context(
            "How do Sightbridge, the IRS DST ruling and the SEC bulletin differ?",
            self.candidates, 0.55,
        )
        self.assertEqual({row["doc_id"] for row in found}, {"sightbridge", "dst", "sec"})

    def test_unrelated_low_score_source_is_not_added(self):
        found = _diverse_named_context("What does Sightbridge propose?", self.candidates, 0.55)
        self.assertNotIn("sec", {row["doc_id"] for row in found})

    def test_neighbor_restores_a_sentence_cut_across_chunks(self):
        first = {"doc_id": "irs", "chunk_no": 1, "title": "IRS Form 8824", "content": "The property must be received by the"}
        second = {"doc_id": "irs", "chunk_no": 2, "title": "IRS Form 8824", "content": "180th day after the transfer."}
        with patch("app.agent.graph.vs.neighboring_passages", return_value=[first, second]) as neighbors:
            found = _complete_split_context([first], None)
        self.assertEqual([row["chunk_no"] for row in found], [1, 2])
        neighbors.assert_called_once_with("irs", 1, role=None)


if __name__ == "__main__":
    unittest.main()

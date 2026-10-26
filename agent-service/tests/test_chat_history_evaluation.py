import unittest

from starlette.requests import Request

from app.admin.security import AdminAuthMiddleware
from app.chat_history import _history_filter


class ChatHistoryEvaluationTests(unittest.TestCase):
    def test_operational_filter_keeps_search_and_person_scope(self):
        where, params = _history_filter("IRS", "person@example.test", include_evaluation=False)
        self.assertIn("NOT is_evaluation", where)
        self.assertIn("actor_email = %s", where)
        self.assertEqual(params, ("IRS", "IRS", "IRS", "IRS", "person@example.test"))

    def test_only_admin_can_classify_history(self):
        request = Request({"type": "http", "method": "PATCH", "path": "/admin/chat-history/123/evaluation", "headers": []})
        middleware = AdminAuthMiddleware(None)
        self.assertTrue(middleware._is_authorized("admin", request))
        self.assertFalse(middleware._is_authorized("viewer", request))
        self.assertFalse(middleware._is_authorized("curator", request))


if __name__ == "__main__":
    unittest.main()

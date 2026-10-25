import unittest
from types import SimpleNamespace
from unittest.mock import patch

from starlette.requests import Request

from app.main import ChatRequest, _resolve_user_id


class ConversationIdentityTests(unittest.TestCase):
    def test_signed_in_account_owns_memory_even_with_browser_id(self):
        request = Request({"type": "http", "headers": []})
        body = ChatRequest(question="Hello", user_id="browser123")
        with patch("app.main.current_actor", return_value=SimpleNamespace(google_sub="verified-sub")):
            self.assertEqual(_resolve_user_id(body, request), "actor:verified-sub")

    def test_public_chat_keeps_browser_scoped_memory(self):
        request = Request({"type": "http", "headers": []})
        body = ChatRequest(question="Hello", user_id="browser123")
        with patch("app.main.current_actor", return_value=None):
            self.assertEqual(_resolve_user_id(body, request), "browser:browser123")


if __name__ == "__main__":
    unittest.main()

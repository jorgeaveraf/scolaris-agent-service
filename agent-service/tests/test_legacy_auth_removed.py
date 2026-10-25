import unittest

from fastapi.testclient import TestClient

from app.main import app


class LegacyAuthenticationRemovalTest(unittest.TestCase):
    def test_password_login_route_is_unavailable(self):
        with TestClient(app) as client:
            response = client.post("/auth/login", json={"password": "unused"})
        self.assertEqual(response.status_code, 404)

    def test_bearer_header_does_not_grant_console_access(self):
        with TestClient(app) as client:
            response = client.get("/admin/docs", headers={"Authorization": "Bearer obsolete-token"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

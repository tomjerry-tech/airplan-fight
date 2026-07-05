import os
import unittest

from app import create_app
from db import get_connection, init_database


class LoginApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        cls.app = create_app().test_client()

    def tearDown(self):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM players WHERE name IN (%s, %s)", ("测试玩家", "abc_123"))

    def test_login_creates_player(self):
        response = self.app.post("/api/login", json={"name": "测试玩家"})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["name"], "测试玩家")
        self.assertIn("player_id", data)
        self.assertEqual(len(data["token"]), 64)

    def test_login_reuses_name(self):
        first = self.app.post("/api/login", json={"name": "abc_123"}).get_json()
        second = self.app.post("/api/login", json={"name": "abc_123"}).get_json()

        self.assertEqual(first["player_id"], second["player_id"])
        self.assertNotEqual(first["token"], second["token"])

    def test_login_rejects_invalid_name(self):
        response = self.app.post("/api/login", json={"name": "a b"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "INVALID_NAME")


if __name__ == "__main__":
    os.environ.setdefault("AIRPLANE_DB_NAME", "airplane_game")
    unittest.main()

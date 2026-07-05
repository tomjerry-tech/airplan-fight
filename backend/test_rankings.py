import os
import unittest

from app import create_app
from db import get_connection, init_database
from rankings import record_score


class RankingsApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        cls.app = create_app().test_client()

    def setUp(self):
        self.players = []

    def tearDown(self):
        names = tuple(player["name"] for player in self.players)
        if not names:
            return
        placeholders = ", ".join(["%s"] * len(names))
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM players WHERE name IN ({})".format(placeholders),
                    names,
                )

    def login(self, name):
        player = self.app.post("/api/login", json={"name": name}).get_json()
        self.players.append(player)
        return player

    def test_rankings_order_by_score(self):
        p1 = self.login("rank_a")
        p2 = self.login("rank_b")
        record_score(p1["player_id"], 100, mode="coop", room_id="111111")
        record_score(p2["player_id"], 300, mode="coop", room_id="111111")

        response = self.app.get("/api/rankings?mode=coop&limit=10")

        self.assertEqual(response.status_code, 200)
        rankings = response.get_json()["rankings"]
        names = [row["name"] for row in rankings[:2]]
        self.assertEqual(names, ["rank_b", "rank_a"])

    def test_rankings_limit(self):
        p1 = self.login("rank_a")
        p2 = self.login("rank_b")
        record_score(p1["player_id"], 100, mode="coop")
        record_score(p2["player_id"], 200, mode="coop")

        response = self.app.get("/api/rankings?mode=coop&limit=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["rankings"]), 1)


if __name__ == "__main__":
    os.environ.setdefault("AIRPLANE_DB_NAME", "airplane_game")
    unittest.main()

import os
import unittest
from datetime import datetime, timedelta

from app import create_app
from db import get_connection, init_database
from rooms import ROOMS, cleanup_expired_rooms, restart_room, reset_rooms


class RoomApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        cls.app = create_app().test_client()

    def setUp(self):
        reset_rooms()
        self.players = []

    def tearDown(self):
        reset_rooms()
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

    def test_create_room(self):
        player = self.login("room_a")
        response = self.app.post("/api/rooms", json=player)

        self.assertEqual(response.status_code, 200)
        room = response.get_json()
        self.assertEqual(room["status"], "waiting")
        self.assertEqual(len(room["room_id"]), 4)
        self.assertTrue(room["room_id"].isdigit())
        self.assertEqual(len(room["players"]), 1)

    def test_join_and_ready_room(self):
        p1 = self.login("room_a")
        p2 = self.login("room_b")
        room = self.app.post("/api/rooms", json=p1).get_json()

        join_response = self.app.post(
            "/api/rooms/{}/join".format(room["room_id"]),
            json=p2,
        )
        self.assertEqual(join_response.status_code, 200)
        self.assertEqual(len(join_response.get_json()["players"]), 2)

        self.app.post("/api/rooms/{}/ready".format(room["room_id"]), json=p1)
        ready_response = self.app.post(
            "/api/rooms/{}/ready".format(room["room_id"]),
            json=p2,
        )

        self.assertEqual(ready_response.status_code, 200)
        self.assertEqual(ready_response.get_json()["status"], "ready")

    def test_room_full(self):
        p1 = self.login("room_a")
        p2 = self.login("room_b")
        p3 = self.login("room_c")
        room = self.app.post("/api/rooms", json=p1).get_json()
        self.app.post("/api/rooms/{}/join".format(room["room_id"]), json=p2)

        response = self.app.post("/api/rooms/{}/join".format(room["room_id"]), json=p3)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "ROOM_FULL")

    def test_leave_closes_empty_room(self):
        player = self.login("room_a")
        room = self.app.post("/api/rooms", json=player).get_json()

        response = self.app.post(
            "/api/rooms/{}/leave".format(room["room_id"]),
            json=player,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "closed")

    def test_restart_room_requires_teammate(self):
        p1 = self.login("room_a")
        room = self.app.post("/api/rooms", json=p1).get_json()

        result, error = restart_room(room["room_id"], p1["player_id"], p1["token"])

        self.assertIsNone(result)
        self.assertEqual(error["error"], "ROOM_NOT_FULL")

    def test_cleanup_expired_waiting_room(self):
        p1 = self.login("room_a")
        room = self.app.post("/api/rooms", json=p1).get_json()
        room_id = room["room_id"]
        ROOMS[room_id]["last_active_at"] = (
            datetime.utcnow() - timedelta(seconds=901)
        ).isoformat() + "Z"

        closed = cleanup_expired_rooms(waiting_timeout=900)

        self.assertEqual(closed, [room_id])
        self.assertNotIn(room_id, ROOMS)
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_room_id FROM players WHERE id = %s", (p1["player_id"],))
                row = cursor.fetchone()
        self.assertIsNone(row["current_room_id"])

    def test_cleanup_keeps_active_waiting_room(self):
        p1 = self.login("room_a")
        room = self.app.post("/api/rooms", json=p1).get_json()

        closed = cleanup_expired_rooms(waiting_timeout=900)

        self.assertEqual(closed, [])
        self.assertIn(room["room_id"], ROOMS)

    def test_cleanup_endpoint(self):
        p1 = self.login("room_a")
        room = self.app.post("/api/rooms", json=p1).get_json()
        room_id = room["room_id"]
        ROOMS[room_id]["last_active_at"] = (
            datetime.utcnow() - timedelta(seconds=901)
        ).isoformat() + "Z"

        response = self.app.post("/api/rooms/cleanup")

        self.assertEqual(response.status_code, 200)
        self.assertIn(room_id, response.get_json()["closed_room_ids"])


if __name__ == "__main__":
    os.environ.setdefault("AIRPLANE_DB_NAME", "airplane_game")
    unittest.main()

import os
import unittest

from app import create_app, socketio
from db import get_connection, init_database
from game_engine import reset_games
from rooms import reset_rooms
from socket_events import CONNECTED_CLIENTS


class SocketEventsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()
        cls.flask_app = create_app()
        cls.http = cls.flask_app.test_client()

    def setUp(self):
        reset_rooms()
        reset_games()
        CONNECTED_CLIENTS.clear()
        self.players = []

    def tearDown(self):
        reset_rooms()
        reset_games()
        CONNECTED_CLIENTS.clear()
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
        player = self.http.post("/api/login", json={"name": name}).get_json()
        self.players.append(player)
        return player

    def test_join_ready_starts_game(self):
        p1 = self.login("sock_a")
        p2 = self.login("sock_b")
        room = self.http.post("/api/rooms", json=p1).get_json()
        client1 = socketio.test_client(self.flask_app)
        client2 = socketio.test_client(self.flask_app)

        client1.emit("join_room", {"room_id": room["room_id"], **p1})
        client2.emit("join_room", {"room_id": room["room_id"], **p2})
        client1.emit("player_ready", {"room_id": room["room_id"], **p1})
        client2.emit("player_ready", {"room_id": room["room_id"], **p2})

        received = client1.get_received() + client2.get_received()
        names = [event["name"] for event in received]
        self.assertIn("room_update", names)
        self.assertIn("game_start", names)

    def test_join_room_rejects_invalid_token(self):
        p1 = self.login("sock_a")
        room = self.http.post("/api/rooms", json=p1).get_json()
        client = socketio.test_client(self.flask_app)

        client.emit(
            "join_room",
            {"room_id": room["room_id"], "player_id": p1["player_id"], "token": "bad"},
        )

        received = client.get_received()
        self.assertEqual(received[0]["name"], "error")
        self.assertEqual(received[0]["args"][0]["error"], "UNAUTHORIZED")

    def test_input_broadcasts_game_state(self):
        p1 = self.login("sock_a")
        p2 = self.login("sock_b")
        room = self.http.post("/api/rooms", json=p1).get_json()
        client1 = socketio.test_client(self.flask_app)
        client2 = socketio.test_client(self.flask_app)

        client1.emit("join_room", {"room_id": room["room_id"], **p1})
        client2.emit("join_room", {"room_id": room["room_id"], **p2})
        client1.emit("player_ready", {"room_id": room["room_id"], **p1})
        client2.emit("player_ready", {"room_id": room["room_id"], **p2})
        client1.get_received()
        client2.get_received()

        client1.emit(
            "input",
            {
                "room_id": room["room_id"],
                "player_id": p1["player_id"],
                "keys": {"right": True},
            },
        )

        received = client1.get_received()
        game_states = [event for event in received if event["name"] == "game_state"]
        self.assertTrue(game_states)
        state = game_states[-1]["args"][0]
        self.assertEqual(state["room_id"], room["room_id"])
        self.assertGreaterEqual(state["tick"], 1)
        self.assertIn("players", state)
        self.assertIn("bullets", state)
        self.assertIn("enemies", state)

    def test_pause_game_broadcasts_paused_state(self):
        p1 = self.login("sock_a")
        p2 = self.login("sock_b")
        room = self.http.post("/api/rooms", json=p1).get_json()
        client1 = socketio.test_client(self.flask_app)
        client2 = socketio.test_client(self.flask_app)

        client1.emit("join_room", {"room_id": room["room_id"], **p1})
        client2.emit("join_room", {"room_id": room["room_id"], **p2})
        client1.emit("player_ready", {"room_id": room["room_id"], **p1})
        client2.emit("player_ready", {"room_id": room["room_id"], **p2})
        client1.get_received()
        client2.get_received()

        client1.emit("pause_game", {"room_id": room["room_id"], "paused": True, **p1})

        received = client2.get_received()
        game_states = [event for event in received if event["name"] == "game_state"]
        self.assertTrue(game_states)
        state = game_states[-1]["args"][0]
        self.assertTrue(state["paused"])
        self.assertEqual(state["pause_reason"], "{} paused".format(p1["name"]))

    def test_restart_game_broadcasts_new_game_state(self):
        p1 = self.login("sock_a")
        p2 = self.login("sock_b")
        room = self.http.post("/api/rooms", json=p1).get_json()
        client1 = socketio.test_client(self.flask_app)
        client2 = socketio.test_client(self.flask_app)

        client1.emit("join_room", {"room_id": room["room_id"], **p1})
        client2.emit("join_room", {"room_id": room["room_id"], **p2})
        client1.emit("player_ready", {"room_id": room["room_id"], **p1})
        client2.emit("player_ready", {"room_id": room["room_id"], **p2})
        client1.get_received()
        client2.get_received()

        client1.emit("restart_game", {"room_id": room["room_id"], **p1})

        received = client2.get_received()
        names = [event["name"] for event in received]
        self.assertIn("game_start", names)
        game_states = [event for event in received if event["name"] == "game_state"]
        self.assertTrue(game_states)
        states = [event["args"][0] for event in game_states]
        state = states[-1]
        self.assertTrue(any(item["tick"] == 0 for item in states))
        self.assertEqual(state["score"], 0)
        self.assertEqual(state["status"], "playing")
        self.assertFalse(state["paused"])

    def test_disconnect_leaves_room_and_pauses_teammate(self):
        p1 = self.login("sock_a")
        p2 = self.login("sock_b")
        room = self.http.post("/api/rooms", json=p1).get_json()
        client1 = socketio.test_client(self.flask_app)
        client2 = socketio.test_client(self.flask_app)

        client1.emit("join_room", {"room_id": room["room_id"], **p1})
        client2.emit("join_room", {"room_id": room["room_id"], **p2})
        client1.emit("player_ready", {"room_id": room["room_id"], **p1})
        client2.emit("player_ready", {"room_id": room["room_id"], **p2})
        client1.get_received()
        client2.get_received()

        client2.disconnect()

        received = client1.get_received()
        game_states = [event for event in received if event["name"] == "game_state"]
        self.assertTrue(game_states)
        state = game_states[-1]["args"][0]
        self.assertTrue(state["paused"])
        self.assertEqual(state["pause_reason"], "teammate disconnected")


if __name__ == "__main__":
    os.environ.setdefault("AIRPLANE_DB_NAME", "airplane_game")
    unittest.main()

import unittest

from network_client import NetworkClient


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self.data


class FakeHttp:
    def __init__(self):
        self.posts = []
        self.gets = []

    def post(self, url, json):
        self.posts.append((url, json))
        if url.endswith("/api/login"):
            return FakeResponse({"player_id": 1, "name": json["name"], "token": "t"})
        if url.endswith("/api/rooms"):
            return FakeResponse({"room_id": "123456", "status": "waiting"})
        return FakeResponse({"ok": True})

    def get(self, url, params=None):
        self.gets.append((url, params))
        return FakeResponse({"rankings": [{"rank": 1, "score": 100}]})


class FakeSio:
    def __init__(self):
        self.handlers = {}
        self.emits = []
        self.connected_url = None

    def on(self, event, handler):
        self.handlers[event] = handler

    def connect(self, url):
        self.connected_url = url

    def disconnect(self):
        self.connected_url = None

    def emit(self, event, data):
        self.emits.append((event, data))


class NetworkClientTest(unittest.TestCase):
    def test_login_and_create_room(self):
        http = FakeHttp()
        client = NetworkClient(http=http, sio=FakeSio())

        player = client.login("playerA")
        room = client.create_room()

        self.assertEqual(player["player_id"], 1)
        self.assertEqual(room["room_id"], "123456")
        self.assertEqual(http.posts[0][0], "http://127.0.0.1:5000/api/login")

    def test_socket_input_emit(self):
        sio = FakeSio()
        client = NetworkClient(http=FakeHttp(), sio=sio)
        client.login("playerA")

        client.send_input("123456", {"right": True})

        self.assertEqual(sio.emits[0][0], "input")
        self.assertEqual(sio.emits[0][1]["keys"]["right"], True)

    def test_pause_game_emit(self):
        sio = FakeSio()
        client = NetworkClient(http=FakeHttp(), sio=sio)
        client.login("playerA")

        client.pause_game("123456", True)

        self.assertEqual(sio.emits[0][0], "pause_game")
        self.assertTrue(sio.emits[0][1]["paused"])
        self.assertEqual(sio.emits[0][1]["room_id"], "123456")

    def test_restart_game_emit(self):
        sio = FakeSio()
        client = NetworkClient(http=FakeHttp(), sio=sio)
        client.login("playerA")

        client.restart_game("123456")

        self.assertEqual(sio.emits[0][0], "restart_game")
        self.assertEqual(sio.emits[0][1]["room_id"], "123456")

    def test_socket_handlers_update_state(self):
        sio = FakeSio()
        client = NetworkClient(http=FakeHttp(), sio=sio)

        sio.handlers["game_state"]({"tick": 1})
        sio.handlers["error"]({"error": "BAD"})

        self.assertEqual(client.latest_state["tick"], 1)
        self.assertEqual(client.last_error["error"], "BAD")


if __name__ == "__main__":
    unittest.main()

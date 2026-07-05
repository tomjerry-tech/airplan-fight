import requests
import socketio


class NetworkClient:
    def __init__(self, base_url="http://127.0.0.1:5000", http=None, sio=None):
        self.base_url = base_url.rstrip("/")
        self.http = http or requests.Session()
        self.sio = sio or socketio.Client()
        self.player = None
        self.room = None
        self.latest_state = None
        self.last_error = None

        self.sio.on("room_update", self._on_room_update)
        self.sio.on("game_start", self._on_game_start)
        self.sio.on("game_state", self._on_game_state)
        self.sio.on("error", self._on_error)

    def login(self, name):
        data = self._post("/api/login", {"name": name})
        self.player = data
        return data

    def create_room(self):
        self._require_login()
        data = self._post("/api/rooms", self.player)
        self.room = data
        return data

    def join_room_http(self, room_id):
        self._require_login()
        data = self._post("/api/rooms/{}/join".format(room_id), self.player)
        self.room = data
        return data

    def set_ready_http(self, room_id, ready=True):
        self._require_login()
        payload = dict(self.player)
        payload["ready"] = ready
        data = self._post("/api/rooms/{}/ready".format(room_id), payload)
        self.room = data
        return data

    def get_rankings(self, mode="coop", limit=10):
        response = self.http.get(
            self.base_url + "/api/rankings",
            params={"mode": mode, "limit": limit},
        )
        response.raise_for_status()
        return response.json()["rankings"]

    def connect_socket(self):
        self.sio.connect(self.base_url)

    def disconnect_socket(self):
        try:
            self.sio.disconnect()
        except Exception:
            pass

    def join_room_socket(self, room_id):
        self._require_login()
        self.sio.emit("join_room", {"room_id": room_id, **self.player})

    def ready_socket(self, room_id, ready=True):
        self._require_login()
        self.sio.emit("player_ready", {"room_id": room_id, "ready": ready, **self.player})

    def leave_room_socket(self, room_id):
        self._require_login()
        self.sio.emit("leave_room", {"room_id": room_id, **self.player})

    def send_input(self, room_id, keys):
        self._require_login()
        self.sio.emit(
            "input",
            {
                "room_id": room_id,
                "player_id": self.player["player_id"],
                "keys": keys,
            },
        )

    def pause_game(self, room_id, paused=True):
        self._require_login()
        self.sio.emit("pause_game", {"room_id": room_id, "paused": paused, **self.player})

    def restart_game(self, room_id):
        self._require_login()
        self.sio.emit("restart_game", {"room_id": room_id, **self.player})

    def _post(self, path, payload):
        response = self.http.post(self.base_url + path, json=payload)
        response.raise_for_status()
        return response.json()

    def _require_login(self):
        if not self.player:
            raise RuntimeError("login required")

    def _on_room_update(self, data):
        self.room = data

    def _on_game_start(self, data):
        self.room = data

    def _on_game_state(self, data):
        self.latest_state = data

    def _on_error(self, data):
        self.last_error = data

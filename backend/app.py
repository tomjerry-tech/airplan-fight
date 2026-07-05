from flask import Flask, jsonify, request
from flask_socketio import SocketIO

from auth import login_by_name
from rankings import get_rankings
from rooms import cleanup_expired_rooms, create_room, join_room, leave_room, list_rooms, set_ready


socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    app = Flask(__name__)

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        result, error = login_by_name(data.get("name"))
        if error:
            return jsonify(error), 400
        return jsonify(result)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/rankings")
    def rankings():
        mode = request.args.get("mode", "coop")
        limit = request.args.get("limit", 10)
        return jsonify({"rankings": get_rankings(mode=mode, limit=limit)})

    @app.get("/api/rooms")
    def rooms_list():
        return jsonify({"rooms": list_rooms()})

    @app.post("/api/rooms/cleanup")
    def rooms_cleanup():
        return jsonify({"closed_room_ids": cleanup_expired_rooms()})

    @app.post("/api/rooms")
    def rooms_create():
        data = request.get_json(silent=True) or {}
        result, error = create_room(data.get("player_id"), data.get("token"))
        if error:
            return jsonify(error), 400
        return jsonify(result)

    @app.post("/api/rooms/<room_id>/join")
    def rooms_join(room_id):
        data = request.get_json(silent=True) or {}
        result, error = join_room(room_id, data.get("player_id"), data.get("token"))
        if error:
            return jsonify(error), 400
        return jsonify(result)

    @app.post("/api/rooms/<room_id>/ready")
    def rooms_ready(room_id):
        data = request.get_json(silent=True) or {}
        result, error = set_ready(
            room_id,
            data.get("player_id"),
            data.get("token"),
            data.get("ready", True),
        )
        if error:
            return jsonify(error), 400
        return jsonify(result)

    @app.post("/api/rooms/<room_id>/leave")
    def rooms_leave(room_id):
        data = request.get_json(silent=True) or {}
        result, error = leave_room(room_id, data.get("player_id"), data.get("token"))
        if error:
            return jsonify(error), 400
        return jsonify(result)

    socketio.init_app(app)

    from socket_events import register_socket_events

    register_socket_events(socketio)
    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, use_reloader=False)

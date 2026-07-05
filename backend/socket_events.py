from flask import request
from flask_socketio import emit, join_room as socket_join_room, leave_room as socket_leave_room

from game_engine import (
    create_game,
    get_game_generation,
    get_game_state,
    remove_game,
    set_input,
    set_pause,
    step_game,
)
from rooms import join_room, leave_room, restart_room, set_ready


RUNNING_LOOPS = set()
CONNECTED_CLIENTS = {}


def _emit_error(error):
    emit("error", error)


def _start_game_loop(socketio, room_id):
    room_id = str(room_id)
    generation = get_game_generation(room_id)
    loop_key = (room_id, generation)
    if loop_key in RUNNING_LOOPS:
        return
    RUNNING_LOOPS.add(loop_key)
    socketio.start_background_task(_game_loop, socketio, room_id, generation)


def _game_loop(socketio, room_id, generation):
    loop_key = (str(room_id), generation)
    try:
        while True:
            if get_game_generation(room_id) != generation:
                return
            state = step_game(room_id)
            if not state:
                return
            socketio.emit("game_state", state, to=room_id)
            if state.get("status") == "game_over":
                return
            socketio.sleep(1 / 30)
    finally:
        RUNNING_LOOPS.discard(loop_key)


def register_socket_events(socketio):
    @socketio.on("join_room")
    def on_join_room(data):
        data = data or {}
        room_id = str(data.get("room_id", ""))
        result, error = join_room(room_id, data.get("player_id"), data.get("token"))
        if error:
            _emit_error(error)
            return
        socket_join_room(room_id)
        CONNECTED_CLIENTS[request.sid] = {
            "room_id": room_id,
            "player_id": data.get("player_id"),
            "token": data.get("token"),
        }
        emit("room_update", result, to=room_id)
        state = get_game_state(room_id)
        if state:
            emit("game_state", state)

    @socketio.on("player_ready")
    def on_player_ready(data):
        data = data or {}
        room_id = str(data.get("room_id", ""))
        result, error = set_ready(
            room_id,
            data.get("player_id"),
            data.get("token"),
            data.get("ready", True),
        )
        if error:
            _emit_error(error)
            return
        emit("room_update", result, to=room_id)
        if result["status"] == "ready":
            state = create_game(result)
            emit("game_start", result, to=room_id)
            emit("game_state", state, to=room_id)
            _start_game_loop(socketio, room_id)

    @socketio.on("input")
    def on_input(data):
        data = data or {}
        room_id = str(data.get("room_id", ""))
        state = set_input(room_id, data.get("player_id"), data.get("keys") or {})
        if not state:
            _emit_error({"error": "GAME_NOT_FOUND", "message": "游戏尚未开始"})
            return
        emit("game_state", state, to=room_id)

    @socketio.on("pause_game")
    def on_pause_game(data):
        data = data or {}
        room_id = str(data.get("room_id", ""))
        paused = bool(data.get("paused", True))
        player_name = data.get("name") or "player"
        reason = "{} paused".format(player_name) if paused else None
        state = set_pause(room_id, paused=paused, reason=reason)
        if not state:
            _emit_error({"error": "GAME_NOT_FOUND", "message": "娓告垙灏氭湭寮€濮?"})
            return
        emit("game_state", state, to=room_id)

    @socketio.on("restart_game")
    def on_restart_game(data):
        data = data or {}
        room_id = str(data.get("room_id", ""))
        result, error = restart_room(room_id, data.get("player_id"), data.get("token"))
        if error:
            _emit_error(error)
            return
        state = create_game(result)
        emit("room_update", result, to=room_id)
        emit("game_start", result, to=room_id)
        emit("game_state", state, to=room_id)
        _start_game_loop(socketio, room_id)

    @socketio.on("leave_room")
    def on_leave_room(data):
        data = data or {}
        room_id = str(data.get("room_id", ""))
        result, error = leave_room(room_id, data.get("player_id"), data.get("token"))
        if error:
            _emit_error(error)
            return
        CONNECTED_CLIENTS.pop(request.sid, None)
        socket_leave_room(room_id)
        if result["status"] == "closed":
            remove_game(room_id)
            for loop_key in list(RUNNING_LOOPS):
                if loop_key[0] == room_id:
                    RUNNING_LOOPS.discard(loop_key)
        else:
            state = set_pause(room_id, paused=True, reason="teammate left")
            if state:
                emit("game_state", state, to=room_id)
        emit("room_update", result, to=room_id)

    @socketio.on("disconnect")
    def on_disconnect():
        info = CONNECTED_CLIENTS.pop(request.sid, None)
        if not info:
            return
        room_id = str(info.get("room_id", ""))
        result, error = leave_room(room_id, info.get("player_id"), info.get("token"))
        if error:
            return
        if result["status"] == "closed":
            remove_game(room_id)
            for loop_key in list(RUNNING_LOOPS):
                if loop_key[0] == room_id:
                    RUNNING_LOOPS.discard(loop_key)
        else:
            state = set_pause(room_id, paused=True, reason="teammate disconnected")
            if state:
                emit("game_state", state, to=room_id)
            emit("room_update", result, to=room_id)

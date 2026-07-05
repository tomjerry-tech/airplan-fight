import random
import string
from datetime import datetime

from db import get_connection


ROOMS = {}
MAX_PLAYERS = 2
WAITING_ROOM_TIMEOUT_SECONDS = 15 * 60


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


def _parse_iso(value):
    if not value:
        return datetime.utcnow()
    return datetime.fromisoformat(str(value).replace("Z", ""))


def _make_room_id():
    for _ in range(20):
        room_id = "".join(random.choices(string.digits, k=4))
        if room_id not in ROOMS:
            return room_id
    raise RuntimeError("Unable to create room id")


def _public_room(room):
    return {
        "room_id": room["room_id"],
        "status": room["status"],
        "players": list(room["players"]),
        "ready": dict(room["ready"]),
        "created_at": room["created_at"],
        "last_active_at": room["last_active_at"],
    }


def reset_rooms():
    ROOMS.clear()


def cleanup_expired_rooms(now=None, waiting_timeout=WAITING_ROOM_TIMEOUT_SECONDS):
    now = now or datetime.utcnow()
    expired_room_ids = []
    expired_player_ids = []

    for room_id, room in list(ROOMS.items()):
        if room.get("status") != "waiting":
            continue
        last_active_at = _parse_iso(room.get("last_active_at"))
        if (now - last_active_at).total_seconds() < waiting_timeout:
            continue
        expired_room_ids.append(room_id)
        expired_player_ids.extend(player["player_id"] for player in room.get("players", []))
        ROOMS.pop(room_id, None)

    if expired_player_ids:
        placeholders = ", ".join(["%s"] * len(expired_player_ids))
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE players SET current_room_id = NULL WHERE id IN ({})".format(placeholders),
                    tuple(expired_player_ids),
                )

    return expired_room_ids


def verify_player(player_id, token):
    if not player_id or not token:
        return None
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, current_room_id FROM players WHERE id = %s AND token = %s",
                (player_id, token),
            )
            return cursor.fetchone()


def create_room(player_id, token):
    cleanup_expired_rooms()
    player = verify_player(player_id, token)
    if not player:
        return None, {"error": "UNAUTHORIZED", "message": "登录状态无效"}
    if player["current_room_id"]:
        return None, {"error": "ALREADY_IN_ROOM", "message": "玩家已在房间中"}

    room_id = _make_room_id()
    room = {
        "room_id": room_id,
        "status": "waiting",
        "players": [{"player_id": player["id"], "name": player["name"]}],
        "ready": {str(player["id"]): False},
        "created_at": _now_iso(),
        "last_active_at": _now_iso(),
    }
    ROOMS[room_id] = room

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE players SET current_room_id = %s WHERE id = %s",
                (room_id, player["id"]),
            )

    return _public_room(room), None


def join_room(room_id, player_id, token):
    cleanup_expired_rooms()
    player = verify_player(player_id, token)
    if not player:
        return None, {"error": "UNAUTHORIZED", "message": "登录状态无效"}
    if player["current_room_id"] and player["current_room_id"] != room_id:
        return None, {"error": "ALREADY_IN_ROOM", "message": "玩家已在其他房间中"}

    room = ROOMS.get(str(room_id))
    if not room:
        return None, {"error": "ROOM_NOT_FOUND", "message": "房间不存在"}
    if any(p["player_id"] == player["id"] for p in room["players"]):
        return _public_room(room), None
    if room["status"] != "waiting":
        return None, {"error": "ROOM_NOT_WAITING", "message": "房间已开始或已结束"}

    if any(p["player_id"] == player["id"] for p in room["players"]):
        return _public_room(room), None
    if len(room["players"]) >= MAX_PLAYERS:
        return None, {"error": "ROOM_FULL", "message": "房间已满"}

    room["players"].append({"player_id": player["id"], "name": player["name"]})
    room["ready"][str(player["id"])] = False
    room["last_active_at"] = _now_iso()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE players SET current_room_id = %s WHERE id = %s",
                (room["room_id"], player["id"]),
            )

    return _public_room(room), None


def set_ready(room_id, player_id, token, ready=True):
    player = verify_player(player_id, token)
    if not player:
        return None, {"error": "UNAUTHORIZED", "message": "登录状态无效"}

    room = ROOMS.get(str(room_id))
    if not room:
        return None, {"error": "ROOM_NOT_FOUND", "message": "房间不存在"}
    if not any(p["player_id"] == player["id"] for p in room["players"]):
        return None, {"error": "NOT_IN_ROOM", "message": "玩家不在该房间中"}

    room["ready"][str(player["id"])] = bool(ready)
    room["last_active_at"] = _now_iso()
    if len(room["players"]) == MAX_PLAYERS and all(room["ready"].values()):
        room["status"] = "ready"

    return _public_room(room), None


def leave_room(room_id, player_id, token):
    player = verify_player(player_id, token)
    if not player:
        return None, {"error": "UNAUTHORIZED", "message": "登录状态无效"}

    room = ROOMS.get(str(room_id))
    if not room:
        return None, {"error": "ROOM_NOT_FOUND", "message": "房间不存在"}

    room["players"] = [p for p in room["players"] if p["player_id"] != player["id"]]
    room["ready"].pop(str(player["id"]), None)
    room["last_active_at"] = _now_iso()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE players SET current_room_id = NULL WHERE id = %s",
                (player["id"],),
            )

    if not room["players"]:
        ROOMS.pop(str(room_id), None)
        return {"room_id": str(room_id), "status": "closed"}, None

    room["status"] = "waiting"
    return _public_room(room), None


def restart_room(room_id, player_id, token):
    player = verify_player(player_id, token)
    if not player:
        return None, {"error": "UNAUTHORIZED", "message": "登录状态无效"}

    room = ROOMS.get(str(room_id))
    if not room:
        return None, {"error": "ROOM_NOT_FOUND", "message": "房间不存在"}
    if not any(p["player_id"] == player["id"] for p in room["players"]):
        return None, {"error": "NOT_IN_ROOM", "message": "玩家不在该房间中"}
    if len(room["players"]) < MAX_PLAYERS:
        return None, {"error": "ROOM_NOT_FULL", "message": "队友不在房间中"}

    room["status"] = "ready"
    room["ready"] = {str(p["player_id"]): True for p in room["players"]}
    room["last_active_at"] = _now_iso()
    return _public_room(room), None


def list_rooms():
    cleanup_expired_rooms()
    return [_public_room(room) for room in ROOMS.values()]

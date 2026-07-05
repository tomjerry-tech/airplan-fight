import re
import secrets

from db import get_connection


NAME_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9_]{2,12}$")


def normalize_name(raw_name):
    if raw_name is None:
        return ""
    return str(raw_name).strip()


def is_valid_name(name):
    return bool(NAME_RE.fullmatch(name))


def login_by_name(raw_name):
    name = normalize_name(raw_name)
    if not is_valid_name(name):
        return None, {
            "error": "INVALID_NAME",
            "message": "昵称需为 2-12 位中文、英文、数字或下划线",
        }

    token = secrets.token_hex(32)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO players (name, token, is_online, last_login_at)
                VALUES (%s, %s, 1, NOW())
                ON DUPLICATE KEY UPDATE
                    token = VALUES(token),
                    is_online = 1,
                    last_login_at = NOW()
                """,
                (name, token),
            )
            cursor.execute(
                "SELECT id, name, token FROM players WHERE name = %s",
                (name,),
            )
            player = cursor.fetchone()

    return {
        "player_id": player["id"],
        "name": player["name"],
        "token": player["token"],
    }, None

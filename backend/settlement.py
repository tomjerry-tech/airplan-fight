from db import get_connection
from rankings import record_score


def record_room_result(room_id, players, score, duration_sec):
    if not players:
        return None

    player_ids = [player["id"] for player in players]
    player1_id = player_ids[0]
    player2_id = player_ids[1] if len(player_ids) > 1 else None

    score_id = record_score(player1_id, score, mode="coop", room_id=room_id)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rooms_history
                    (room_id, player1_id, player2_id, score, duration_sec)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (room_id, player1_id, player2_id, int(score), int(duration_sec)),
            )
            history_id = cursor.lastrowid

    return {"score_id": score_id, "history_id": history_id}

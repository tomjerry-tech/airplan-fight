from db import get_connection


def record_score(player_id, score, mode="coop", room_id=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scores (player_id, score, mode, room_id)
                VALUES (%s, %s, %s, %s)
                """,
                (player_id, int(score), mode, room_id),
            )
            return cursor.lastrowid


def get_rankings(mode="coop", limit=10):
    limit = max(1, min(int(limit), 50))
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.player_id,
                    p.name,
                    s.score,
                    s.mode,
                    s.room_id,
                    s.created_at
                FROM scores s
                JOIN players p ON p.id = s.player_id
                WHERE s.mode = %s
                ORDER BY s.score DESC, s.created_at ASC
                LIMIT %s
                """,
                (mode, limit),
            )
            rows = cursor.fetchall()

    rankings = []
    for index, row in enumerate(rows, start=1):
        rankings.append(
            {
                "rank": index,
                "score_id": row["id"],
                "player_id": row["player_id"],
                "name": row["name"],
                "score": row["score"],
                "mode": row["mode"],
                "room_id": row["room_id"],
                "created_at": row["created_at"].isoformat()
                if row["created_at"]
                else None,
            }
        )
    return rankings

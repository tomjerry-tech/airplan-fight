import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"


DB_DEFAULTS = {
    "AIRPLANE_DB_HOST": "127.0.0.1",
    "AIRPLANE_DB_PORT": "3306",
    "AIRPLANE_DB_USER": "root",
    "AIRPLANE_DB_PASSWORD": "ljhyjf999",
    "AIRPLANE_DB_NAME": "airplane_game",
}


def submit_local_score(score, mode, player_name="local_player"):
    for key, value in DB_DEFAULTS.items():
        os.environ.setdefault(key, value)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    try:
        from auth import login_by_name
        from db import init_database
        from rankings import record_score

        init_database()
        player, error = login_by_name(player_name)
        if error:
            return {"saved": False, "error": error.get("error", "LOGIN_FAILED")}
        score_id = record_score(player["player_id"], int(score), mode=mode)
        return {"saved": True, "score_id": score_id}
    except Exception as exc:
        return {"saved": False, "error": str(exc)}

import os
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
PYTHON = Path(os.getenv("AIRPLANE_PYTHON", sys.executable))
BACKEND_URL = "http://127.0.0.1:5000"
LOG_PATH = ROOT / "start_dev.log"

DB_ENV_DEFAULTS = {
    "AIRPLANE_DB_HOST": "127.0.0.1",
    "AIRPLANE_DB_PORT": "3306",
    "AIRPLANE_DB_USER": "root",
    "AIRPLANE_DB_NAME": "airplane_game",
}


def make_env():
    env = os.environ.copy()
    for key, value in DB_ENV_DEFAULTS.items():
        env.setdefault(key, value)
    return env


def check_python():
    if not PYTHON.exists():
        raise SystemExit("Python not found: {}".format(PYTHON))


def check_mysql():
    command = [
        str(PYTHON),
        "-c",
        "from backend.db import get_connection; c=get_connection(); c.close(); print('mysql ok')",
    ]
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        env=make_env(),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit("MySQL check failed. Make sure MySQL is running.")


def start_backend():
    return subprocess.Popen(
        [str(PYTHON), str(ROOT / "backend" / "app.py")],
        cwd=str(ROOT),
        env=make_env(),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def backend_health():
    try:
        response = requests.get(BACKEND_URL + "/api/health", timeout=1)
        return response.status_code == 200
    except requests.RequestException:
        return False


def backend_port_responds():
    try:
        requests.get(BACKEND_URL, timeout=1)
        return True
    except requests.RequestException as exc:
        return getattr(exc, "response", None) is not None


def wait_backend(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if backend_health():
            return
        time.sleep(0.5)
    raise SystemExit("Backend did not become ready at {}".format(BACKEND_URL))


def start_client(extra_args):
    return subprocess.Popen(
        [str(PYTHON), str(ROOT / "code" / "online_game.py")] + extra_args,
        cwd=str(ROOT),
        env=make_env(),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def create_demo_room():
    suffix = str(int(time.time()))[-5:]
    player_a_name = "pA{}".format(suffix)
    player_b_name = "pB{}".format(suffix)

    response = requests.post(BACKEND_URL + "/api/login", json={"name": player_a_name}, timeout=5)
    response.raise_for_status()
    player_a = response.json()

    response = requests.post(BACKEND_URL + "/api/rooms", json=player_a, timeout=5)
    response.raise_for_status()
    room = response.json()

    response = requests.post(BACKEND_URL + "/api/login", json={"name": player_b_name}, timeout=5)
    response.raise_for_status()
    player_b = response.json()
    response = requests.post(
        BACKEND_URL + "/api/rooms/{}/join".format(room["room_id"]),
        json=player_b,
        timeout=5,
    )
    response.raise_for_status()

    return room["room_id"], player_a_name, player_b_name


def main():
    LOG_PATH.write_text("", encoding="utf-8")
    check_python()
    check_mysql()
    if backend_health():
        print("Backend already running, reusing it.")
    else:
        if backend_port_responds():
            raise SystemExit(
                "Port 5000 is occupied by an old backend. Close that Flask window and run again."
            )
        print("Starting backend...")
        start_backend()
        wait_backend()
    print("Backend ready.")
    room_id, player_a, player_b = create_demo_room()
    print("Created room:", room_id)
    print("Starting two clients...")
    start_client(["--name", player_a, "--room", room_id])
    start_client(["--name", player_b, "--room", room_id])
    print("Started. Clients should enter room {} automatically.".format(room_id))
    print("Keep this window open. Press Ctrl+C here to stop the dev launcher.")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit as exc:
        LOG_PATH.write_text("SystemExit: {}\n".format(exc), encoding="utf-8")
        print("start_dev stopped:", exc)
        input("Press Enter to close...")
        sys.exit(1)
    except Exception as exc:
        LOG_PATH.write_text("{}\n".format(exc), encoding="utf-8")
        print("start_dev failed:", exc)
        input("Press Enter to close...")
        sys.exit(1)

import argparse
import time

from network_client import NetworkClient


def main():
    parser = argparse.ArgumentParser(description="Online client smoke demo")
    parser.add_argument("--server", default="http://127.0.0.1:5000")
    parser.add_argument("--name", required=True)
    parser.add_argument("--room")
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()

    client = NetworkClient(base_url=args.server)
    player = client.login(args.name)
    print("logged in:", player["player_id"], player["name"])

    if args.create:
        room = client.create_room()
        room_id = room["room_id"]
        print("created room:", room_id)
    elif args.room:
        room_id = args.room
        room = client.join_room_http(room_id)
        print("joined room:", room["room_id"])
    else:
        raise SystemExit("Use --create or --room ROOM_ID")

    client.connect_socket()
    client.join_room_socket(room_id)
    client.ready_socket(room_id, True)
    print("socket ready, press Ctrl+C to stop")

    try:
        while True:
            client.send_input(room_id, {"left": False, "right": False, "up": False, "down": False})
            if client.latest_state:
                print("tick:", client.latest_state["tick"], "score:", client.latest_state["score"])
            if client.last_error:
                print("error:", client.last_error)
                client.last_error = None
            time.sleep(1)
    except KeyboardInterrupt:
        client.leave_room_socket(room_id)
        client.disconnect_socket()


if __name__ == "__main__":
    main()

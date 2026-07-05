import argparse
import subprocess
import sys
from pathlib import Path

import pygame

from network_client import NetworkClient
from online_lobby import LobbyState, STATE_STARTING, draw_lobby, handle_lobby_event, load_font
from resource_manager import resource_manager as res
from settings import SCREEN_HEIGHT, SCREEN_WIDTH, FPS


COLORS = {
    "background": (12, 18, 32),
    "player": (80, 180, 255),
    "player_dead": (70, 70, 80),
    "enemy": (255, 90, 90),
    "bullet": (255, 240, 120),
    "boss_bullet": (220, 80, 255),
    "gem": (100, 255, 180),
    "item": (255, 180, 80),
    "boss": (180, 90, 255),
    "text": (230, 235, 245),
}
ENEMY_MAX_HP = {1: 3, 2: 7, 3: 12}


def format_ticks(ticks):
    if ticks is None:
        return "--:--"
    seconds = max(0, int(ticks) // 30)
    return "{:02d}:{:02d}".format(seconds // 60, seconds % 60)

POST_GAME_BUTTONS = {
    "again": pygame.Rect(32, 510, 130, 46),
    "menu": pygame.Rect(175, 510, 130, 46),
    "rankings": pygame.Rect(318, 510, 130, 46),
}
RANKINGS_CLOSE_BUTTON = pygame.Rect(165, 585, 150, 42)
PAUSE_BUTTON = pygame.Rect(SCREEN_WIDTH - 48, 10, 36, 34)
PAUSE_MENU_BUTTONS = {
    "resume": pygame.Rect(140, 316, 200, 46),
    "menu": pygame.Rect(140, 382, 200, 46),
}


def load_assets():
    try:
        res.load_all_resources()
        return {
            "players": res.get_image("hero"),
            "players_damaged": res.get_image("damaged"),
            "players_death": res.get_image("death"),
            "enemy1": res.get_image("enemy1"),
            "enemy2": res.get_image("enemy2"),
            "enemy3": res.get_image("enemy3_n"),
            "enemy1_down": res.get_image("enemy1_down"),
            "enemy2_down": res.get_image("enemy2_down"),
            "enemy3_down": res.get_image("enemy3_down"),
            "enemy2_hit": res.get_image("enemy2_hit"),
            "enemy3_hit": res.get_image("enemy3_hit"),
            "bullet": res.get_image("bullet"),
            "boss_bullet": res.get_image("enemy_bullet"),
            "gem1": res.get_image("gem1"),
            "gem2": res.get_image("gem2"),
            "gem3": res.get_image("gem3"),
            "gem4": res.get_image("gem4"),
            "heal": res.get_image("item_heal"),
            "shield": res.get_image("item_shield"),
            "upgrade": res.get_image("item_upgrade"),
            "track": res.get_image("item_track"),
            "shield_effect": res.get_image("item_shield"),
            "boss": res.get_image("boss_idle"),
        }
    except Exception as exc:
        print("asset load failed, fallback to shapes:", exc)
        return {}


def load_audio():
    try:
        return {
            "background": res.get_sound("background"),
            "boss": res.get_sound("bgm_boss"),
            "warning": res.get_sound("warning"),
            "bullet": res.get_sound("bullet"),
            "enemy_down": res.get_sound("enemy1_down"),
            "boom": res.get_sound("boom_l"),
            "crystal": res.get_sound("crystal"),
            "shield": res.get_sound("shield"),
            "life": res.get_sound("life"),
            "upgrade": res.get_sound("upgrade"),
            "rush": res.get_sound("rush"),
            "player_down": res.get_sound("me_down"),
        }
    except Exception as exc:
        print("audio load failed:", exc)
        return {}


def stop_music(audio):
    for key in ("background", "boss"):
        sound = audio.get(key)
        if sound:
            sound.stop()


def play_music(audio, key, current_key):
    if current_key == key:
        return current_key
    stop_music(audio)
    sound = audio.get(key)
    if sound:
        sound.play(-1)
    return key


def play_sound(audio, key):
    sound = audio.get(key)
    if sound:
        sound.play()


def launch_main_menu():
    root = Path(__file__).resolve().parent
    subprocess.Popen([sys.executable, str(root / "main_menu.py")], cwd=str(root))


def game_over_button_at(pos):
    for key, rect in POST_GAME_BUTTONS.items():
        if rect.collidepoint(pos):
            return key
    return None


def rankings_close_at(pos):
    return RANKINGS_CLOSE_BUTTON.collidepoint(pos)


def pause_button_at(pos):
    return PAUSE_BUTTON.collidepoint(pos)


def pause_menu_button_at(pos):
    for key, rect in PAUSE_MENU_BUTTONS.items():
        if rect.collidepoint(pos):
            return key
    return None


def player_result_rows(state):
    rows = []
    for player in (state or {}).get("players", []):
        status = "ALIVE" if player.get("alive") else "DOWN"
        rows.append(
            "{}  HP:{}  {}".format(
                player.get("name", "Player"),
                player.get("hp", 0),
                status,
            )
        )
    return rows


def fetch_rankings(client):
    try:
        return client.get_rankings(mode="coop", limit=10), None
    except Exception as exc:
        return [], str(exc)


class AudioState:
    def __init__(self):
        self.previous = None
        self.music = None

    def update(self, audio, state):
        if not audio or not state:
            return

        if state.get("status") == "boss_warning":
            self.music = play_music(audio, "background", self.music)
            if not self.previous or self.previous.get("status") != "boss_warning":
                play_sound(audio, "warning")
        elif state.get("boss"):
            self.music = play_music(audio, "boss", self.music)
        elif state.get("status") == "game_over":
            stop_music(audio)
            self.music = None
        else:
            self.music = play_music(audio, "background", self.music)

        if self.previous:
            self._play_delta_sounds(audio, self.previous, state)
        self.previous = state

    def _play_delta_sounds(self, audio, previous, current):
        prev_dead_enemies = {enemy["id"] for enemy in previous.get("dead_enemies", [])}
        for enemy in current.get("dead_enemies", []):
            if enemy["id"] not in prev_dead_enemies and enemy.get("death_timer", 0) <= 1:
                play_sound(audio, "enemy_down")

        prev_items = {item["id"] for item in previous.get("items", [])}
        current_items = {item["id"] for item in current.get("items", [])}
        if len(current_items) < len(prev_items):
            play_sound(audio, "crystal")

        prev_players = {player["id"]: player for player in previous.get("players", [])}
        for player in current.get("players", []):
            old = prev_players.get(player["id"])
            if not old:
                continue
            if player.get("hp", 0) < old.get("hp", 0):
                play_sound(audio, "boom")
            if old.get("alive", True) and not player.get("alive", True):
                play_sound(audio, "player_down")
            if player.get("shield_timer", 0) > old.get("shield_timer", 0):
                play_sound(audio, "shield")
            if player.get("power_level", 0) > old.get("power_level", 0):
                play_sound(audio, "upgrade")
            if player.get("berserk_timer", 0) > old.get("berserk_timer", 0):
                play_sound(audio, "rush")


def keys_to_input(keys):
    return {
        "left": bool(keys[pygame.K_LEFT] or keys[pygame.K_a]),
        "right": bool(keys[pygame.K_RIGHT] or keys[pygame.K_d]),
        "up": bool(keys[pygame.K_UP] or keys[pygame.K_w]),
        "down": bool(keys[pygame.K_DOWN] or keys[pygame.K_s]),
    }


def rect_from_center(obj, width, height):
    return pygame.Rect(
        int(obj["x"] - width / 2),
        int(obj["y"] - height / 2),
        width,
        height,
    )


def get_asset(assets, category, obj=None):
    if not assets:
        return None
    if category == "player":
        if (obj or {}).get("alive") is False:
            return _animated_asset(assets.get("players_death"), (obj or {}).get("death_timer", 0), 8)
        if (obj or {}).get("damage_timer", 0) > 0:
            return _animated_asset(assets.get("players_damaged"), (obj or {}).get("damage_timer", 0), 4)
        return _first_asset(assets.get("players"))
    if category == "enemy":
        enemy_type = (obj or {}).get("type", 1)
        hp = (obj or {}).get("hp")
        if enemy_type in (2, 3) and hp is not None and hp < ENEMY_MAX_HP.get(enemy_type, hp):
            return _first_asset(assets.get("enemy{}_hit".format(enemy_type)))
        return _first_asset(assets.get("enemy{}".format(enemy_type)))
    if category == "dead_enemy":
        enemy_type = (obj or {}).get("type", 1)
        return _animated_asset(
            assets.get("enemy{}_down".format(enemy_type)),
            (obj or {}).get("death_timer", 0),
            6,
        )
    if category == "bullet":
        if (obj or {}).get("type") == "track":
            return _indexed_asset(assets.get("bullet"), 3)
        if (obj or {}).get("type") == "berserk":
            return _indexed_asset(assets.get("bullet"), 1)
        return _first_asset(assets.get("bullet"))
    if category == "boss_bullet":
        return _first_asset(assets.get("boss_bullet"))
    if category == "item":
        if (obj or {}).get("type") == "gem":
            return _first_asset(assets.get("gem{}".format((obj or {}).get("level", 1))))
        return _first_asset(assets.get((obj or {}).get("type")))
    if category == "boss":
        return _first_asset(assets.get("boss"))
    return None


def _animated_asset(value, tick, frame_len=8):
    if isinstance(value, list) and value:
        index = (int(tick) // frame_len) % len(value)
        return value[index]
    return value


def _indexed_asset(value, index):
    if isinstance(value, list) and value:
        return value[min(index, len(value) - 1)]
    return value


def _first_asset(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def blit_center(screen, image, obj):
    rect = image.get_rect(center=(int(obj["x"]), int(obj["y"])))
    screen.blit(image, rect)


def draw_state(screen, font, state, assets=None):
    assets = assets or {}
    screen.fill(COLORS["background"])
    if not state:
        text = font.render("waiting for game_state", True, COLORS["text"])
        screen.blit(text, (20, 20))
        return

    if state.get("status") == "boss_warning":
        warning = font.render("WARNING", True, (255, 50, 70))
        rect = warning.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        if (state.get("boss_warning_timer", 0) // 8) % 2 == 0:
            screen.blit(warning, rect)

    for item in state.get("items", []):
        image = get_asset(assets, "item", item)
        if image:
            blit_center(screen, image, item)
        else:
            color = COLORS["gem"] if item.get("type") == "gem" else COLORS["item"]
            pygame.draw.rect(screen, color, rect_from_center(item, 14, 14))

    for enemy in state.get("enemies", []):
        image = get_asset(assets, "enemy", enemy)
        if image:
            blit_center(screen, image, enemy)
        else:
            pygame.draw.rect(screen, COLORS["enemy"], rect_from_center(enemy, 34, 28))

    for enemy in state.get("dead_enemies", []):
        image = get_asset(assets, "dead_enemy", enemy)
        if image:
            blit_center(screen, image, enemy)
        else:
            pygame.draw.circle(screen, COLORS["enemy"], (int(enemy["x"]), int(enemy["y"])), 24, 2)

    boss = state.get("boss")
    if boss:
        image = get_asset(assets, "boss", boss)
        if image:
            if boss.get("visible", True):
                blit_center(screen, image, boss)
            else:
                ghost = image.copy()
                ghost.set_alpha(90)
                blit_center(screen, ghost, boss)
        else:
            pygame.draw.rect(screen, COLORS["boss"], rect_from_center(boss, 120, 70), 3)
        max_hp = max(1, boss.get("max_hp", boss.get("hp", 1)))
        ratio = max(0, min(1, boss.get("hp", 0) / max_hp))
        bar_w, bar_h = 260, 12
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        pygame.draw.rect(screen, (35, 30, 46), (bar_x, 8, bar_w, bar_h))
        pygame.draw.rect(screen, (220, 48, 82), (bar_x, 8, int(bar_w * ratio), bar_h))
        pygame.draw.rect(screen, (245, 230, 255), (bar_x, 8, bar_w, bar_h), 1)
        hp_text = font.render("BOSS {}".format(boss["hp"]), True, COLORS["text"])
        screen.blit(hp_text, (SCREEN_WIDTH // 2 - 45, 24))
        if boss.get("phase") == 2:
            phase_text = font.render("PHASE 2", True, (255, 190, 90))
            screen.blit(phase_text, (SCREEN_WIDTH // 2 - 42, 44))
        if not boss.get("visible", True):
            cloak_text = font.render("CLOAK", True, (180, 150, 255))
            screen.blit(cloak_text, (SCREEN_WIDTH // 2 - 30, 64))
        if boss.get("invincible_timer", 0) > 0:
            pygame.draw.circle(screen, (180, 130, 255), (int(boss["x"]), int(boss["y"])), 80, 2)

    for bullet in state.get("bullets", []):
        image = get_asset(assets, "bullet", bullet)
        if image:
            blit_center(screen, image, bullet)
        else:
            pygame.draw.rect(screen, COLORS["bullet"], rect_from_center(bullet, 6, 16))

    for bullet in state.get("boss_bullets", []):
        image = get_asset(assets, "boss_bullet", bullet)
        if image:
            blit_center(screen, image, bullet)
        else:
            size = 18 if bullet.get("type") == "boss_burst" else 10
            color = (255, 120, 80) if bullet.get("type") == "boss_burst" else COLORS["boss_bullet"]
            if bullet.get("type") == "boss_spiral":
                color = (180, 110, 255)
            pygame.draw.rect(screen, color, rect_from_center(bullet, size, size))

    for player in state.get("players", []):
        image = get_asset(assets, "player", player)
        if image:
            blit_center(screen, image, player)
        else:
            color = COLORS["player"] if player.get("alive") else COLORS["player_dead"]
            pygame.draw.rect(screen, color, rect_from_center(player, 34, 42))
        if player.get("shield_timer", 0) > 0:
            shield = _first_asset(assets.get("shield_effect"))
            if shield:
                shield_rect = shield.get_rect(center=(int(player["x"] + 26), int(player["y"] - 28)))
                screen.blit(shield, shield_rect)
            pygame.draw.circle(screen, (110, 210, 255), (int(player["x"]), int(player["y"])), 38, 2)
        label = font.render("{} HP:{}".format(player["name"], player["hp"]), True, COLORS["text"])
        screen.blit(label, (int(player["x"] - 35), int(player["y"] + 26)))

    hud = font.render(
        "tick:{} score:{} time:{} status:{}".format(
            state.get("tick", 0),
            state.get("score", 0),
            format_ticks(state.get("remaining_ticks")),
            state.get("status", "unknown"),
        ),
        True,
        COLORS["text"],
    )
    screen.blit(hud, (12, SCREEN_HEIGHT - 30))
    draw_pause_button(screen)
    if state.get("paused"):
        draw_pause_overlay(screen, font, state)


def draw_pause_button(screen):
    pygame.draw.rect(screen, (36, 45, 78), PAUSE_BUTTON, border_radius=6)
    pygame.draw.rect(screen, (225, 235, 255), PAUSE_BUTTON, width=2, border_radius=6)
    x = PAUSE_BUTTON.left + 11
    y = PAUSE_BUTTON.top + 8
    pygame.draw.rect(screen, (235, 240, 250), (x, y, 4, 18), border_radius=1)
    pygame.draw.rect(screen, (235, 240, 250), (x + 10, y, 4, 18), border_radius=1)


def draw_pause_overlay(screen, font, state):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 8, 18, 178))
    screen.blit(overlay, (0, 0))

    title_font = load_font(32, True)
    title = title_font.render("PAUSED", True, (255, 232, 245))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 236)))

    reason = state.get("pause_reason") or "Game paused"
    rendered_reason = font.render(reason, True, (205, 214, 238))
    screen.blit(rendered_reason, rendered_reason.get_rect(center=(SCREEN_WIDTH // 2, 278)))

    _draw_button(screen, font, PAUSE_MENU_BUTTONS["resume"], "RESUME", (82, 148, 238))
    _draw_button(screen, font, PAUSE_MENU_BUTTONS["menu"], "MAIN MENU", (236, 103, 181))


def draw_game_over(screen, font, state, rankings=None, show_rankings=False, error=None):
    screen.fill((13, 16, 31))
    title_font = load_font(34, True)
    score_font = load_font(30, True)

    title = title_font.render("GAME OVER", True, (255, 232, 245))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 86)))

    score = (state or {}).get("score", 0)
    score_text = score_font.render("SCORE {}".format(score), True, (255, 210, 90))
    screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, 142)))

    panel = pygame.Rect(48, 190, 384, 292)
    pygame.draw.rect(screen, (24, 28, 55), panel, border_radius=8)
    pygame.draw.rect(screen, (210, 220, 255), panel, width=2, border_radius=8)

    if show_rankings:
        _draw_rankings_panel(screen, font, rankings or [], error)
    else:
        _draw_result_panel(screen, font, state)

    _draw_button(screen, font, POST_GAME_BUTTONS["again"], "PLAY AGAIN", (74, 180, 130))
    _draw_button(screen, font, POST_GAME_BUTTONS["menu"], "MAIN MENU", (82, 148, 238))
    _draw_button(screen, font, POST_GAME_BUTTONS["rankings"], "RANKINGS", (236, 103, 181))


def _draw_result_panel(screen, font, state):
    header = font.render("Players", True, (235, 240, 250))
    screen.blit(header, (82, 220))
    y = 262
    for row in player_result_rows(state):
        rendered = font.render(row, True, (220, 230, 245))
        screen.blit(rendered, (82, y))
        y += 38
    settlement = (state or {}).get("settlement") or {}
    if settlement:
        saved = font.render("Saved to coop leaderboard", True, (170, 220, 180))
    else:
        saved = font.render("Waiting for leaderboard save", True, (190, 190, 210))
    screen.blit(saved, (82, 430))


def _draw_rankings_panel(screen, font, rankings, error=None):
    header = font.render("Coop Top 10", True, (235, 240, 250))
    screen.blit(header, (82, 220))
    if error:
        rendered = font.render("Ranking load failed", True, (255, 170, 170))
        screen.blit(rendered, (82, 272))
        return
    if not rankings:
        rendered = font.render("No ranking records", True, (190, 190, 210))
        screen.blit(rendered, (82, 272))
        return
    y = 255
    for row in rankings[:6]:
        text = "#{:<2} {:<12} {}".format(
            row.get("rank", 0),
            str(row.get("name", "Player"))[:12],
            row.get("score", 0),
        )
        rendered = font.render(text, True, (220, 230, 245))
        screen.blit(rendered, (82, y))
        y += 30


def _draw_button(screen, font, rect, text, color):
    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, (245, 248, 255), rect, width=2, border_radius=8)
    rendered = font.render(text, True, (255, 255, 255))
    screen.blit(rendered, rendered.get_rect(center=rect.center))


def run_online_game(args):
    client = NetworkClient(base_url=args.server)
    room_id = None
    lobby = LobbyState()
    in_lobby = not (args.name and (args.create or args.room))

    if args.name and in_lobby:
        client.login(args.name)
        lobby.name = args.name
        lobby.submit_name()

    if args.name and not in_lobby:
        player = client.login(args.name)
        if args.create:
            room = client.create_room()
            room_id = room["room_id"]
            print("created room:", room_id)
        else:
            if not args.room:
                raise SystemExit("Use --create or --room ROOM_ID")
            room_id = args.room
            client.join_room_http(room_id)
            print("joined room:", room_id)
        client.connect_socket()
        client.join_room_socket(room_id)
        client.ready_socket(room_id, True)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Online Airplane Game")
    font = load_font(18)
    assets = load_assets()
    audio = load_audio()
    audio_state = AudioState()
    clock = pygame.time.Clock()
    send_timer = 0
    start_delay = 0
    rankings = []
    rankings_error = None
    show_rankings = False
    last_state_status = None

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if (
                    not in_lobby
                    and client.latest_state
                    and client.latest_state.get("status") == "game_over"
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                ):
                    action = game_over_button_at(event.pos)
                    if action == "again" and room_id:
                        client.restart_game(room_id)
                        show_rankings = False
                    if action == "menu":
                        launch_main_menu()
                        return
                    if action == "rankings":
                        rankings, rankings_error = fetch_rankings(client)
                        show_rankings = True
                elif (
                    not in_lobby
                    and client.latest_state
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and room_id
                ):
                    if client.latest_state.get("paused"):
                        action = pause_menu_button_at(event.pos)
                        if action == "resume":
                            client.pause_game(room_id, False)
                        elif action == "menu":
                            client.leave_room_socket(room_id)
                            launch_main_menu()
                            return
                    elif pause_button_at(event.pos):
                        client.pause_game(room_id, True)
                elif (
                    not in_lobby
                    and client.latest_state
                    and event.type == pygame.KEYDOWN
                    and event.key == pygame.K_ESCAPE
                    and room_id
                ):
                    client.pause_game(room_id, not client.latest_state.get("paused"))
                elif in_lobby:
                    action = handle_lobby_event(lobby, event)
                    if action == "login":
                        client.login(lobby.name)
                    elif action == "create":
                        room = client.create_room()
                        room_id = room["room_id"]
                        lobby.set_waiting(room_id)
                        lobby.apply_room_update(room)
                        client.connect_socket()
                        client.join_room_socket(room_id)
                    elif action == "join":
                        room_id = lobby.room_id
                        room = client.join_room_http(room_id)
                        lobby.apply_room_update(room)
                        client.connect_socket()
                        client.join_room_socket(room_id)
                        client.ready_socket(room_id, True)
                    elif action == "rankings":
                        lobby_rankings, lobby_error = fetch_rankings(client)
                        lobby.show_rankings(lobby_rankings, lobby_error)

            if in_lobby and client.room:
                lobby.apply_room_update(client.room)
                if room_id and len(client.room.get("players", [])) == 2:
                    client.ready_socket(room_id, True)

            if in_lobby and client.latest_state and lobby.state == STATE_STARTING:
                start_delay += 1
                if start_delay >= 45:
                    in_lobby = False
            elif in_lobby and client.latest_state and not args.name:
                start_delay = 0

            if in_lobby and client.latest_state and args.name:
                in_lobby = False

            if in_lobby:
                draw_lobby(screen, font, lobby)
            else:
                is_game_over = bool(client.latest_state and client.latest_state.get("status") == "game_over")
                is_paused = bool(client.latest_state and client.latest_state.get("paused"))
                current_status = client.latest_state.get("status") if client.latest_state else None
                if last_state_status == "game_over" and current_status != "game_over":
                    rankings = []
                    rankings_error = None
                    show_rankings = False
                    audio_state.previous = None
                last_state_status = current_status
                send_timer += 1
                if send_timer >= 3 and room_id and not is_game_over and not is_paused:
                    send_timer = 0
                    client.send_input(room_id, keys_to_input(pygame.key.get_pressed()))
                audio_state.update(audio, client.latest_state)
                if is_game_over:
                    draw_game_over(screen, font, client.latest_state, rankings, show_rankings, rankings_error)
                else:
                    draw_state(screen, font, client.latest_state, assets)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        stop_music(audio)
        if room_id and client.player:
            client.leave_room_socket(room_id)
        client.disconnect_socket()
        pygame.quit()


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Pygame online client")
    parser.add_argument("--server", default="http://127.0.0.1:5000")
    parser.add_argument("--name")
    parser.add_argument("--room")
    parser.add_argument("--create", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    run_online_game(parse_args(sys.argv[1:]))

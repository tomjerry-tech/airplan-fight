import os
import argparse
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pygame

from settings import FPS, SCREEN_HEIGHT, SCREEN_WIDTH


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
IMAGES = ROOT / "assets" / "images"
DEFAULT_BACKEND_URL = "http://127.0.0.1:5000"
BACKEND_URL = os.getenv("AIRPLANE_SERVER_URL", DEFAULT_BACKEND_URL).rstrip("/")
BACKEND_ENV = {
    "AIRPLANE_DB_HOST": "127.0.0.1",
    "AIRPLANE_DB_PORT": "3306",
    "AIRPLANE_DB_USER": "root",
    "AIRPLANE_DB_PASSWORD": "ljhyjf999",
    "AIRPLANE_DB_NAME": "airplane_game",
}

TEXT = {
    "title": "\u5854\u83f2\u55b5\u7a7a\u6218",
    "login_title": "\u8f93\u5165\u6635\u79f0",
    "login_hint": "2-12 \u4f4d\u4e2d\u6587/\u82f1\u6587/\u6570\u5b57/_",
    "login_button": "\u8fdb\u5165\u6e38\u620f",
    "login_error": "\u6635\u79f0\u4e0d\u5408\u6cd5\u6216\u540e\u7aef\u672a\u542f\u52a8",
    "login_placeholder": "\u70b9\u51fb\u8f93\u5165\u6635\u79f0",
    "default_name": "\u968f\u673a\u6635\u79f0",
    "choose": "\u9009\u62e9\u6a21\u5f0f",
    "single": "\u5355\u4eba\u6a21\u5f0f",
    "single_sub": "5 \u5206\u949f\u9650\u65f6",
    "endless": "\u65e0\u5c3d\u6a21\u5f0f",
    "endless_sub": "\u65e0\u65f6\u95f4\u7ec8\u70b9",
    "online": "\u53cc\u4eba\u6a21\u5f0f",
    "online_sub": "\u8054\u7f51\u521b\u5efa/\u52a0\u5165\u623f\u95f4",
    "rankings": "\u6392\u884c\u699c",
    "rankings_sub": "\u67e5\u770b\u5355\u4eba/\u65e0\u5c3d/\u53cc\u4eba",
    "rankings_title": "\u6392\u884c\u699c",
    "rankings_empty": "\u6682\u65e0\u8bb0\u5f55",
    "rankings_error": "\u6392\u884c\u699c\u52a0\u8f7d\u5931\u8d25",
    "back": "\u8fd4\u56de",
    "single_rank": "\u5355\u4eba",
    "endless_rank": "\u65e0\u5c3d",
    "coop_rank": "\u53cc\u4eba",
    "exit": "ESC \u9000\u51fa",
    "player": "\u73a9\u5bb6",
}
LOGIN_BUTTON = pygame.Rect(90, 470, 300, 54)
NAME_INPUT = pygame.Rect(90, 385, 300, 58)
DEFAULT_NAME_BUTTON = pygame.Rect(318, 333, 72, 34)
RANKINGS_BACK_BUTTON = pygame.Rect(165, 592, 150, 42)
RANKING_TABS = [
    ("single", TEXT["single_rank"], pygame.Rect(54, 178, 112, 42)),
    ("endless", TEXT["endless_rank"], pygame.Rect(184, 178, 112, 42)),
    ("coop", TEXT["coop_rank"], pygame.Rect(314, 178, 112, 42)),
]


@dataclass
class MenuOption:
    key: str
    label: str
    subtitle: str
    rect: pygame.Rect


def build_options():
    width = 320
    height = 58
    x = (SCREEN_WIDTH - width) // 2
    return [
        MenuOption("single", TEXT["single"], TEXT["single_sub"], pygame.Rect(x, 300, width, height)),
        MenuOption("endless", TEXT["endless"], TEXT["endless_sub"], pygame.Rect(x, 368, width, height)),
        MenuOption("online", TEXT["online"], TEXT["online_sub"], pygame.Rect(x, 436, width, height)),
        MenuOption("rankings", TEXT["rankings"], TEXT["rankings_sub"], pygame.Rect(x, 504, width, height)),
    ]


def option_at(options, pos):
    for option in options:
        if option.rect.collidepoint(pos):
            return option.key
    return None


def backend_ready():
    try:
        with urllib.request.urlopen(BACKEND_URL + "/api/health", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def set_backend_url(url):
    global BACKEND_URL
    BACKEND_URL = (url or DEFAULT_BACKEND_URL).rstrip("/")


def is_local_backend():
    parsed = urllib.parse.urlparse(BACKEND_URL)
    return parsed.hostname in ("127.0.0.1", "localhost", "::1")


def login_player(name):
    if not ensure_backend():
        return None
    payload = json.dumps({"name": name}).encode("utf-8")
    request = urllib.request.Request(
        BACKEND_URL + "/api/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def default_player_name():
    return "player{}".format(int(time.time() * 1000) % 10000)


def append_login_text(current, text, limit=12):
    allowed = []
    for char in text:
        if char == "_":
            allowed.append(char)
        elif "\u4e00" <= char <= "\u9fa5":
            allowed.append(char)
        elif char.isascii() and char.isalnum():
            allowed.append(char)
    return (current + "".join(allowed))[:limit]


def submit_login(name):
    target_name = name.strip() or default_player_name()
    return target_name, login_player(target_name)


def fetch_menu_rankings(mode="single", limit=10):
    if not ensure_backend():
        return [], TEXT["rankings_error"]
    query = urllib.parse.urlencode({"mode": mode, "limit": limit})
    try:
        with urllib.request.urlopen(BACKEND_URL + "/api/rankings?" + query, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("rankings", []), None
    except Exception:
        return [], TEXT["rankings_error"]


def ensure_backend():
    if backend_ready():
        return True
    if not is_local_backend():
        return False

    env = os.environ.copy()
    env.update(BACKEND_ENV)
    subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "backend" / "app.py")],
        cwd=str(PROJECT_ROOT),
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )

    deadline = time.time() + 12
    while time.time() < deadline:
        if backend_ready():
            return True
        time.sleep(0.5)
    return False


def launch_mode(mode, player_name=None):
    player_name = player_name or "local_player"
    if mode in ("single", "endless"):
        script = ROOT / "test.py"
        subprocess.Popen([sys.executable, str(script), "--mode", mode, "--name", player_name], cwd=str(ROOT))
        return
    if mode == "online":
        ensure_backend()
        script = ROOT / "online_game.py"
        subprocess.Popen(
            [sys.executable, str(script), "--server", BACKEND_URL, "--name", player_name],
            cwd=str(ROOT),
        )
        return
    raise ValueError("unknown mode: {}".format(mode))


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Airplane game main menu")
    parser.add_argument("--server", default=os.getenv("AIRPLANE_SERVER_URL", DEFAULT_BACKEND_URL))
    return parser.parse_args(argv)


def load_background():
    path = IMAGES / "start2.png"
    if path.exists():
        image = pygame.image.load(str(path)).convert()
        return pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    return None


def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("arial", size, bold=bold)


def draw_center_text(screen, font, text, y, color):
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, y))
    screen.blit(rendered, rect)


def draw_base(screen, fonts, background=None):
    if background:
        screen.blit(background, (0, 0))
    else:
        screen.fill((14, 18, 38))

    shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    shade.fill((10, 12, 32, 92))
    screen.blit(shade, (0, 0))

    draw_center_text(screen, fonts["title"], TEXT["title"], 82, (255, 244, 255))


def draw_login(screen, fonts, name, error, active=True, background=None):
    draw_base(screen, fonts, background)
    draw_center_text(screen, fonts["button"], TEXT["login_title"], 250, (255, 245, 255))
    draw_center_text(screen, fonts["small"], TEXT["login_hint"], 292, (230, 235, 255))

    pygame.draw.rect(screen, (22, 24, 54), NAME_INPUT, border_radius=8)
    border = (255, 255, 255) if active else (245, 218, 255)
    pygame.draw.rect(screen, border, NAME_INPUT, width=2, border_radius=8)
    shown_name = name or TEXT["login_placeholder"]
    text_color = (255, 255, 255) if name else (172, 178, 210)
    rendered = fonts["button"].render(shown_name, True, text_color)
    screen.blit(rendered, (NAME_INPUT.left + 18, NAME_INPUT.top + 15))
    if active and int(time.time() * 2) % 2 == 0:
        caret_x = min(NAME_INPUT.right - 18, NAME_INPUT.left + 22 + rendered.get_width())
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (caret_x, NAME_INPUT.top + 14),
            (caret_x, NAME_INPUT.bottom - 14),
            2,
        )

    pygame.draw.rect(screen, (74, 180, 130), DEFAULT_NAME_BUTTON, border_radius=8)
    pygame.draw.rect(screen, (238, 242, 255), DEFAULT_NAME_BUTTON, width=2, border_radius=8)
    default_text = fonts["small"].render(TEXT["default_name"], True, (255, 255, 255))
    screen.blit(default_text, default_text.get_rect(center=DEFAULT_NAME_BUTTON.center))

    pygame.draw.rect(screen, (236, 103, 181), LOGIN_BUTTON, border_radius=8)
    pygame.draw.rect(screen, (245, 248, 255), LOGIN_BUTTON, width=2, border_radius=8)
    btn = fonts["button"].render(TEXT["login_button"], True, (255, 255, 255))
    screen.blit(btn, btn.get_rect(center=LOGIN_BUTTON.center))
    if error:
        draw_center_text(screen, fonts["small"], TEXT["login_error"], 545, (255, 175, 175))
    draw_center_text(screen, fonts["small"], TEXT["exit"], 640, (230, 230, 242))


def draw_menu(screen, options, fonts, background=None, hover_key=None, player_name=""):
    draw_base(screen, fonts, background)
    draw_center_text(screen, fonts["small"], TEXT["choose"], 128, (232, 235, 255))
    if player_name:
        draw_center_text(
            screen,
            fonts["small"],
            "{}: {}".format(TEXT["player"], player_name),
            158,
            (232, 235, 255),
        )

    panel = pygame.Rect(50, 286, 380, 292)
    pygame.draw.rect(screen, (22, 24, 54), panel, border_radius=8)
    pygame.draw.rect(screen, (245, 218, 255), panel, width=2, border_radius=8)

    for option in options:
        active = option.key == hover_key
        fill = (236, 103, 181) if option.key == "online" else (82, 148, 238)
        if option.key == "endless":
            fill = (90, 105, 210)
        if option.key == "rankings":
            fill = (74, 180, 130)
        if not active:
            fill = tuple(max(0, c - 24) for c in fill)
        pygame.draw.rect(screen, fill, option.rect, border_radius=8)
        pygame.draw.rect(screen, (238, 242, 255), option.rect, width=2, border_radius=8)
        label = fonts["button"].render(option.label, True, (255, 255, 255))
        subtitle = fonts["small"].render(option.subtitle, True, (235, 238, 255))
        screen.blit(label, (option.rect.left + 24, option.rect.top + 9))
        screen.blit(subtitle, (option.rect.left + 170, option.rect.top + 22))

    draw_center_text(screen, fonts["small"], TEXT["exit"], 640, (230, 230, 242))


def draw_rankings(screen, fonts, rows, mode, error=None, background=None):
    draw_base(screen, fonts, background)
    draw_center_text(screen, fonts["button"], TEXT["rankings_title"], 132, (255, 245, 255))

    for tab_mode, label, rect in RANKING_TABS:
        fill = (236, 103, 181) if tab_mode == mode else (50, 58, 100)
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, (238, 242, 255), rect, width=2, border_radius=8)
        text = fonts["small"].render(label, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=rect.center))

    panel = pygame.Rect(50, 238, 380, 328)
    pygame.draw.rect(screen, (22, 24, 54), panel, border_radius=8)
    pygame.draw.rect(screen, (245, 218, 255), panel, width=2, border_radius=8)

    if error:
        draw_center_text(screen, fonts["small"], error, 392, (255, 175, 175))
    elif not rows:
        draw_center_text(screen, fonts["small"], TEXT["rankings_empty"], 392, (230, 235, 255))
    else:
        for index, row in enumerate(rows[:10]):
            line = "#{:<2} {:<12} {}".format(
                row.get("rank", index + 1),
                str(row.get("name", ""))[:12],
                row.get("score", 0),
            )
            rendered = fonts["small"].render(line, True, (238, 242, 255))
            screen.blit(rendered, (80, 258 + index * 29))

    pygame.draw.rect(screen, (82, 148, 238), RANKINGS_BACK_BUTTON, border_radius=8)
    pygame.draw.rect(screen, (238, 242, 255), RANKINGS_BACK_BUTTON, width=2, border_radius=8)
    back = fonts["button"].render(TEXT["back"], True, (255, 255, 255))
    screen.blit(back, back.get_rect(center=RANKINGS_BACK_BUTTON.center))
    draw_center_text(screen, fonts["small"], TEXT["exit"], 650, (230, 230, 242))


def run_menu():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Airplane Game")
    pygame.key.start_text_input()
    pygame.key.set_text_input_rect(NAME_INPUT)
    clock = pygame.time.Clock()
    fonts = {
        "title": load_font(36, True),
        "button": load_font(24, True),
        "small": load_font(15),
    }
    options = build_options()
    background = load_background()
    login_name = ""
    player = None
    login_error = False
    login_input_active = True
    screen_state = "menu"
    ranking_mode = "single"
    ranking_rows = []
    ranking_error = None

    while True:
        hover_key = option_at(options, pygame.mouse.get_pos())
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if player and screen_state == "rankings":
                    screen_state = "menu"
                    continue
                pygame.quit()
                return
            if not player and event.type == pygame.TEXTINPUT and login_input_active:
                login_name = append_login_text(login_name, event.text)
                login_error = False
            elif not player and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    login_name = login_name[:-1]
                elif event.key == pygame.K_RETURN:
                    login_name, player = submit_login(login_name)
                    login_error = not bool(player)
            elif not player and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if NAME_INPUT.collidepoint(event.pos):
                    login_input_active = True
                    pygame.key.set_text_input_rect(NAME_INPUT)
                    login_error = False
                elif DEFAULT_NAME_BUTTON.collidepoint(event.pos):
                    login_name = default_player_name()
                    login_input_active = True
                    login_error = False
                elif LOGIN_BUTTON.collidepoint(event.pos):
                    login_name, player = submit_login(login_name)
                    login_error = not bool(player)
                else:
                    login_input_active = False
            elif player and screen_state == "rankings" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if RANKINGS_BACK_BUTTON.collidepoint(event.pos):
                    screen_state = "menu"
                    continue
                for tab_mode, _label, rect in RANKING_TABS:
                    if rect.collidepoint(event.pos):
                        ranking_mode = tab_mode
                        ranking_rows, ranking_error = fetch_menu_rankings(ranking_mode)
                        break
            elif player and screen_state == "menu" and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                ranking_mode = "single"
                ranking_rows, ranking_error = fetch_menu_rankings(ranking_mode)
                screen_state = "rankings"
            elif player and screen_state == "menu" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                selected = option_at(options, event.pos)
                if selected:
                    if selected == "rankings":
                        ranking_mode = "single"
                        ranking_rows, ranking_error = fetch_menu_rankings(ranking_mode)
                        screen_state = "rankings"
                        continue
                    pygame.quit()
                    launch_mode(selected, player["name"])
                    return

        if player and screen_state == "rankings":
            draw_rankings(screen, fonts, ranking_rows, ranking_mode, ranking_error, background)
        elif player:
            draw_menu(screen, options, fonts, background, hover_key, player["name"])
        else:
            draw_login(screen, fonts, login_name, login_error, login_input_active, background)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    set_backend_url(args.server)
    run_menu()

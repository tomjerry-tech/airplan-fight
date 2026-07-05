import pygame
from pathlib import Path


STATE_NAME = "name"
STATE_MENU = "menu"
STATE_JOIN = "join"
STATE_WAITING = "waiting"
STATE_STARTING = "starting"
STATE_RANKINGS = "rankings"

TEXT = {
    "title": "\u8054\u673a\u5927\u5385",
    "name_prompt": "\u8f93\u5165\u6635\u79f0",
    "name_error": "\u6635\u79f0\u81f3\u5c11 2 \u4f4d",
    "menu_prompt": "\u9009\u62e9\u521b\u5efa\u623f\u95f4\u6216\u52a0\u5165\u623f\u95f4\u7801",
    "create": "\u521b\u5efa\u623f\u95f4",
    "join": "\u52a0\u5165\u623f\u95f4\u7801",
    "rankings": "\u6392\u884c\u699c",
    "room_prompt": "\u8f93\u5165 4 \u4f4d\u623f\u95f4\u7801",
    "room_error": "\u623f\u95f4\u7801\u5fc5\u987b\u662f 4 \u4f4d\u6570\u5b57",
    "waiting": "\u623f\u95f4\u5df2\u521b\u5efa\uff0c\u7b49\u5f85\u961f\u53cb\u8f93\u5165\u623f\u95f4\u7801",
    "starting": "\u4e24\u540d\u73a9\u5bb6\u5df2\u51c6\u5907\uff0c\u5373\u5c06\u540c\u65f6\u5f00\u59cb",
    "nickname": "\u6635\u79f0",
    "room_code": "\u623f\u95f4\u7801",
    "players": "\u73a9\u5bb6",
    "share": "\u961f\u53cb\u52a0\u5165\u540e\uff0c\u53cc\u65b9\u81ea\u52a8\u5f00\u59cb",
    "coop_top": "\u5408\u4f5c\u6a21\u5f0f TOP 10",
    "no_rankings": "\u6682\u65e0\u6392\u884c\u8bb0\u5f55",
    "rankings_error": "\u6392\u884c\u699c\u52a0\u8f7d\u5931\u8d25",
    "enter": "\u8fdb\u5165",
    "back": "\u8fd4\u56de",
}

COLORS = {
    "bg": (12, 18, 32),
    "panel": (22, 25, 54),
    "line": (205, 220, 255),
    "text": (235, 240, 250),
    "muted": (166, 178, 210),
    "blue": (82, 148, 238),
    "pink": (236, 103, 181),
    "dark": (35, 40, 82),
}


class LobbyState:
    def __init__(self):
        self.state = STATE_NAME
        self.name = ""
        self.room_id = ""
        self.message = "Enter nickname"
        self.players = []
        self.rankings = []
        self.rankings_error = None

    def handle_text(self, text):
        if self.state == STATE_NAME:
            self.name = append_name_text(self.name, text)
        elif self.state == STATE_JOIN:
            if text.isdigit() and len(self.room_id) < 4:
                self.room_id += text

    def backspace(self):
        if self.state == STATE_NAME:
            self.name = self.name[:-1]
        elif self.state == STATE_JOIN:
            self.room_id = self.room_id[:-1]

    def submit_name(self):
        if len(self.name.strip()) < 2:
            self.message = "Name must be at least 2 chars"
            return False
        self.name = self.name.strip()
        self.state = STATE_MENU
        self.message = "Create or join a room"
        return True

    def start_join(self):
        self.state = STATE_JOIN
        self.message = "Enter room id"

    def submit_join(self):
        if len(self.room_id.strip()) != 4:
            self.message = "Room id must be 4 digits"
            return False
        self.room_id = self.room_id.strip()
        self.state = STATE_WAITING
        self.message = "Waiting for room"
        return True

    def set_waiting(self, room_id):
        self.room_id = str(room_id)
        self.state = STATE_WAITING
        self.message = "Room {} created, waiting for teammate".format(self.room_id)

    def apply_room_update(self, room):
        if not room:
            return
        self.room_id = str(room.get("room_id", self.room_id))
        self.players = room.get("players", [])
        if room.get("status") == "ready":
            self.state = STATE_STARTING
            self.message = "Teammate joined, starting game"
        elif self.state == STATE_WAITING:
            self.message = "Room {}, waiting for teammate".format(self.room_id)

    def show_rankings(self, rankings=None, error=None):
        self.rankings = rankings or []
        self.rankings_error = error
        self.state = STATE_RANKINGS
        self.message = "Rankings"

    def back_to_menu(self):
        self.state = STATE_MENU
        self.message = "Create or join a room"


def button_rects():
    return {
        "submit_name": pygame.Rect(90, 405, 300, 50),
        "create": pygame.Rect(80, 326, 320, 50),
        "join": pygame.Rect(80, 392, 320, 50),
        "rankings": pygame.Rect(80, 458, 320, 50),
        "submit_join": pygame.Rect(90, 420, 300, 50),
        "rankings_back": pygame.Rect(150, 500, 180, 44),
    }


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


def append_name_text(current, text, limit=12):
    allowed = []
    for char in text:
        if char == "_":
            allowed.append(char)
        elif "\u4e00" <= char <= "\u9fa5":
            allowed.append(char)
        elif char.isascii() and char.isalnum():
            allowed.append(char)
    return (current + "".join(allowed))[:limit]


def draw_lobby(screen, font, lobby):
    screen.fill(COLORS["bg"])
    _draw_center(screen, font, TEXT["title"], 72, COLORS["text"])

    panel = pygame.Rect(50, 150, 380, 410)
    pygame.draw.rect(screen, COLORS["panel"], panel, border_radius=8)
    pygame.draw.rect(screen, COLORS["line"], panel, width=2, border_radius=8)

    if lobby.state == STATE_NAME:
        _draw_name(screen, font, lobby)
    elif lobby.state == STATE_MENU:
        _draw_menu(screen, font, lobby)
    elif lobby.state == STATE_JOIN:
        _draw_join(screen, font, lobby)
    elif lobby.state == STATE_WAITING:
        _draw_waiting(screen, font, lobby)
    elif lobby.state == STATE_STARTING:
        _draw_starting(screen, font, lobby)
    elif lobby.state == STATE_RANKINGS:
        _draw_rankings(screen, font, lobby)


def _draw_name(screen, font, lobby):
    _draw_label(screen, font, TEXT["name_prompt"], 195)
    _draw_input(screen, font, lobby.name or TEXT["nickname"], 246)
    if lobby.message.startswith("Name"):
        _draw_center(screen, font, TEXT["name_error"], 325, (255, 170, 170))
    _draw_button(screen, font, button_rects()["submit_name"], TEXT["enter"], COLORS["blue"])


def _draw_menu(screen, font, lobby):
    _draw_center(screen, font, "{}: {}".format(TEXT["nickname"], lobby.name), 210, COLORS["muted"])
    _draw_center(screen, font, TEXT["menu_prompt"], 252, COLORS["text"])
    _draw_button(screen, font, button_rects()["create"], TEXT["create"], COLORS["pink"])
    _draw_button(screen, font, button_rects()["join"], TEXT["join"], COLORS["blue"])
    _draw_button(screen, font, button_rects()["rankings"], TEXT["rankings"], (74, 180, 130))


def _draw_join(screen, font, lobby):
    _draw_label(screen, font, TEXT["room_prompt"], 195)
    _draw_input(screen, font, lobby.room_id, 246)
    if lobby.message.startswith("Room id must"):
        _draw_center(screen, font, TEXT["room_error"], 325, (255, 170, 170))
    _draw_button(screen, font, button_rects()["submit_join"], TEXT["join"], COLORS["blue"])


def _draw_waiting(screen, font, lobby):
    _draw_center(screen, font, TEXT["waiting"], 205, COLORS["text"])
    _draw_room_code(screen, font, lobby.room_id)
    _draw_center(
        screen,
        font,
        "{}: {}/2".format(TEXT["players"], len(lobby.players)),
        380,
        COLORS["muted"],
    )
    _draw_player_names(screen, font, lobby.players, 405)
    _draw_center(screen, font, TEXT["share"], 430, COLORS["muted"])


def _draw_starting(screen, font, lobby):
    _draw_center(screen, font, TEXT["starting"], 230, COLORS["text"])
    _draw_room_code(screen, font, lobby.room_id)
    _draw_center(
        screen,
        font,
        "{}: {}/2".format(TEXT["players"], len(lobby.players)),
        410,
        COLORS["muted"],
    )
    _draw_player_names(screen, font, lobby.players, 435)


def _draw_rankings(screen, font, lobby):
    _draw_center(screen, font, TEXT["coop_top"], 195, COLORS["text"])
    if lobby.rankings_error:
        _draw_center(screen, font, TEXT["rankings_error"], 285, (255, 170, 170))
    elif not lobby.rankings:
        _draw_center(screen, font, TEXT["no_rankings"], 285, COLORS["muted"])
    else:
        y = 235
        for row in lobby.rankings[:7]:
            text = "#{:<2} {:<12} {}".format(
                row.get("rank", 0),
                str(row.get("name", "Player"))[:12],
                row.get("score", 0),
            )
            rendered = font.render(text, True, COLORS["text"])
            screen.blit(rendered, (100, y))
            y += 32
    _draw_button(screen, font, button_rects()["rankings_back"], TEXT["back"], COLORS["blue"])


def _draw_label(screen, font, text, y):
    rendered = font.render(text, True, COLORS["muted"])
    screen.blit(rendered, (90, y))


def _draw_input(screen, font, text, y):
    rect = pygame.Rect(90, y, 300, 54)
    pygame.draw.rect(screen, COLORS["dark"], rect, border_radius=8)
    pygame.draw.rect(screen, COLORS["line"], rect, width=2, border_radius=8)
    rendered = font.render(text, True, COLORS["text"])
    screen.blit(rendered, (rect.left + 18, rect.top + 15))


def _draw_room_code(screen, font, room_id):
    code_font = load_font(46, True)
    _draw_center(screen, font, TEXT["room_code"], 272, COLORS["muted"])
    _draw_center(screen, code_font, str(room_id), 322, (255, 245, 255))


def _draw_player_names(screen, font, players, y):
    names = [str(player.get("name", "")) for player in players if player.get("name")]
    if not names:
        return
    _draw_center(screen, font, " / ".join(names[:2]), y, COLORS["text"])


def _draw_button(screen, font, rect, text, color):
    pygame.draw.rect(screen, color, rect, border_radius=8)
    pygame.draw.rect(screen, (245, 248, 255), rect, width=2, border_radius=8)
    rendered = font.render(text, True, (255, 255, 255))
    screen.blit(rendered, rendered.get_rect(center=rect.center))


def _draw_center(screen, font, text, y, color):
    rendered = font.render(text, True, color)
    screen.blit(rendered, rendered.get_rect(center=(screen.get_width() // 2, y)))


def handle_lobby_event(lobby, event):
    if event.type == pygame.TEXTINPUT:
        lobby.handle_text(event.text)
        return None

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        rects = button_rects()
        if lobby.state == STATE_NAME and rects["submit_name"].collidepoint(event.pos):
            return "login" if lobby.submit_name() else None
        if lobby.state == STATE_MENU and rects["create"].collidepoint(event.pos):
            lobby.state = STATE_WAITING
            lobby.message = "Creating room"
            return "create"
        if lobby.state == STATE_MENU and rects["join"].collidepoint(event.pos):
            lobby.start_join()
            return None
        if lobby.state == STATE_MENU and rects["rankings"].collidepoint(event.pos):
            return "rankings"
        if lobby.state == STATE_JOIN and rects["submit_join"].collidepoint(event.pos):
            return "join" if lobby.submit_join() else None
        if lobby.state == STATE_RANKINGS and rects["rankings_back"].collidepoint(event.pos):
            lobby.back_to_menu()
            return None
        return None

    if event.type != pygame.KEYDOWN:
        return None
    if event.key == pygame.K_BACKSPACE:
        lobby.backspace()
        return None
    if event.key == pygame.K_ESCAPE:
        if lobby.state == STATE_JOIN:
            lobby.back_to_menu()
        elif lobby.state == STATE_RANKINGS:
            lobby.back_to_menu()
        return None
    if event.key == pygame.K_RETURN:
        if lobby.state == STATE_NAME and lobby.submit_name():
            return "login"
        if lobby.state == STATE_JOIN and lobby.submit_join():
            return "join"
        return None
    if lobby.state == STATE_MENU and event.key == pygame.K_c:
        lobby.state = STATE_WAITING
        lobby.message = "Creating room"
        return "create"
    if lobby.state == STATE_MENU and event.key == pygame.K_j:
        lobby.start_join()
        return None
    if lobby.state == STATE_MENU and event.key == pygame.K_r:
        return "rankings"
    if event.unicode and event.unicode.isprintable():
        lobby.handle_text(event.unicode)
    return None

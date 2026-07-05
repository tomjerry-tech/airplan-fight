import math
import random

from settlement import record_room_result


SCREEN_WIDTH = 480
SCREEN_HEIGHT = 700
PLAYER_SPEED = 5
BULLET_SPEED = 12
ENEMY_SPEED = 2
BULLET_HIT_RADIUS = 24
ITEM_PICKUP_RADIUS = 28
PLAYER_HIT_RADIUS = 30
GAME_DURATION_TICKS = 30 * 5 * 60
ENEMY_HP = {1: 3, 2: 7, 3: 12}
ENEMY_SCORE = {1: 1, 2: 3, 3: 5}
INITIAL_BOSS_SCORE = 20
BOSS_WARNING_TICKS = 60
BOSS_HIT_RADIUS = 60
BOSS_BULLET_HIT_RADIUS = 24
BOSS_BULLET_SPEED = 5
BOSS_BASE_HP = 90
BOSS_HP_PER_PLAYER = 35
BOSS_SCORE = 50
BOSS_PHASE_INVINCIBLE_TICKS = 90
BOSS_CLOAK_INTERVAL = 360
BOSS_CLOAK_TICKS = 90
BOSS_SPIRAL_INTERVAL = 150
BOSS_BURST_INTERVAL = 240
ITEM_DROP_RATE = 0.2
ITEM_TYPES = ["heal", "shield", "upgrade", "track"]
ENEMY_GEM_DROP = {
    1: [(1, 0.8), (2, 0.25)],
    2: [(1, 0.6), (2, 0.4), (3, 0.15), (4, 0.05)],
    3: [(2, 0.5), (3, 0.4), (4, 0.12)],
}
GEM_SCORE = {1: 1, 2: 3, 3: 5, 4: 10}
GEM_MAGNET_RADIUS = 120
GEM_MAGNET_SPEED = 4
BERSERK_DURATION = 480
TRACK_DURATION = 600
AUTO_SHIELD_SCORE = 5000
AUTO_SHIELD_INTERVAL = 1800

GAMES = {}


def reset_games():
    GAMES.clear()


def create_game(room):
    room_id = room["room_id"]
    previous = GAMES.get(str(room_id))
    generation = (previous or {}).get("_generation", 0) + 1
    players = {}
    start_x = [SCREEN_WIDTH // 2 - 40, SCREEN_WIDTH // 2 + 40]
    for index, player in enumerate(room["players"]):
        players[str(player["player_id"])] = {
            "id": player["player_id"],
            "name": player["name"],
            "x": start_x[index],
            "y": SCREEN_HEIGHT - 90,
            "hp": 10,
            "alive": True,
            "shield_timer": 0,
            "damage_timer": 0,
            "death_timer": 0,
            "power_level": 0,
            "berserk_timer": 0,
            "track_timer": 0,
        }

    state = {
        "room_id": room_id,
        "_generation": generation,
        "tick": 0,
        "score": 0,
        "status": "playing",
        "paused": False,
        "pause_reason": None,
        "players": players,
        "inputs": {},
        "bullets": [],
        "boss_bullets": [],
        "enemies": [],
        "dead_enemies": [],
        "items": [],
        "boss": None,
        "boss_warning_timer": 0,
        "_boss_threshold": INITIAL_BOSS_SCORE,
        "_next_bullet_id": 1,
        "_next_boss_bullet_id": 1,
        "_next_enemy_id": 1,
        "_next_item_id": 1,
        "_shoot_timer": 0,
        "_boss_shoot_timer": 0,
        "_boss_cloak_timer": 0,
        "_boss_spiral_timer": 0,
        "_boss_burst_timer": 0,
        "_auto_shield_timer": 0,
        "_enemy_timer": 0,
        "_settled": False,
        "time_limit_ticks": GAME_DURATION_TICKS,
        "end_reason": None,
    }
    GAMES[room_id] = state
    return public_state(state)


def remove_game(room_id):
    GAMES.pop(str(room_id), None)


def get_game_state(room_id):
    state = GAMES.get(str(room_id))
    if not state:
        return None
    return public_state(state)


def get_game_generation(room_id):
    state = GAMES.get(str(room_id))
    if not state:
        return None
    return state.get("_generation", 0)


def set_input(room_id, player_id, keys):
    state = GAMES.get(str(room_id))
    if not state:
        return None
    state["inputs"][str(player_id)] = {
        "left": bool(keys.get("left")),
        "right": bool(keys.get("right")),
        "up": bool(keys.get("up")),
        "down": bool(keys.get("down")),
    }
    return public_state(state)


def set_pause(room_id, paused=True, reason=None):
    state = GAMES.get(str(room_id))
    if not state:
        return None
    if state["status"] == "game_over":
        return public_state(state)
    state["paused"] = bool(paused)
    state["pause_reason"] = reason if paused else None
    return public_state(state)


def step_game(room_id):
    state = GAMES.get(str(room_id))
    if not state:
        return None
    if state["status"] == "game_over":
        return public_state(state)
    if state.get("paused"):
        return public_state(state)

    state["tick"] += 1
    _update_timers(state)
    _update_boss_warning(state)
    _update_players(state)
    _apply_auto_shield(state)
    _spawn_bullets(state)
    _update_bullets(state)
    _update_dead_enemies(state)
    _maybe_spawn_boss(state)
    _spawn_boss_bullets(state)
    _spawn_enemy_bullets(state)
    _update_boss_bullets(state)
    _spawn_enemies(state)
    _update_enemies(state)
    _check_bullet_enemy_collisions(state)
    _check_bullet_boss_collisions(state)
    _check_boss_bullet_player_collisions(state)
    _check_enemy_player_collisions(state)
    _check_item_pickups(state)
    _check_time_limit(state)
    _check_game_over(state)
    return public_state(state)


def _update_players(state):
    for player_id, player in state["players"].items():
        keys = state["inputs"].get(player_id, {})
        dx = int(keys.get("right", False)) - int(keys.get("left", False))
        dy = int(keys.get("down", False)) - int(keys.get("up", False))
        player["x"] = max(20, min(SCREEN_WIDTH - 20, player["x"] + dx * PLAYER_SPEED))
        player["y"] = max(40, min(SCREEN_HEIGHT - 40, player["y"] + dy * PLAYER_SPEED))


def _apply_auto_shield(state):
    if state["score"] < AUTO_SHIELD_SCORE:
        return
    state["_auto_shield_timer"] += 1
    if state["_auto_shield_timer"] < AUTO_SHIELD_INTERVAL:
        return
    state["_auto_shield_timer"] = 0
    for player in state["players"].values():
        if player["alive"]:
            player["shield_timer"] = max(player.get("shield_timer", 0), 180)


def _update_timers(state):
    for player in state["players"].values():
        player["shield_timer"] = max(0, player.get("shield_timer", 0) - 1)
        player["damage_timer"] = max(0, player.get("damage_timer", 0) - 1)
        player["berserk_timer"] = max(0, player.get("berserk_timer", 0) - 1)
        player["track_timer"] = max(0, player.get("track_timer", 0) - 1)
        if not player.get("alive", True):
            player["death_timer"] = player.get("death_timer", 0) + 1
    if state.get("boss"):
        boss = state["boss"]
        boss["invincible_timer"] = max(0, boss.get("invincible_timer", 0) - 1)
        boss["cloak_timer"] = max(0, boss.get("cloak_timer", 0) - 1)


def _spawn_bullets(state):
    state["_shoot_timer"] += 1
    if state["_shoot_timer"] < 6:
        return
    state["_shoot_timer"] = 0
    for player in state["players"].values():
        if not player["alive"]:
            continue
        if player.get("berserk_timer", 0) > 0:
            offsets = [-30, -15, 0, 15, 30]
            bullet_type = "track" if player.get("track_timer", 0) > 0 else "berserk"
            speed = BULLET_SPEED + 3
        else:
            count = min(1 + player.get("power_level", 0), 3)
            offsets = [0] if count == 1 else [-10, 10] if count == 2 else [-16, 0, 16]
            bullet_type = "track" if player.get("track_timer", 0) > 0 else "normal"
            speed = BULLET_SPEED
        for offset in offsets:
            vx = 0
            if player.get("berserk_timer", 0) > 0:
                vx = offset / 5
            bullet_id = state["_next_bullet_id"]
            state["_next_bullet_id"] += 1
            state["bullets"].append(
                {
                    "id": "b{}".format(bullet_id),
                    "owner_id": player["id"],
                    "type": bullet_type,
                    "x": player["x"] + offset,
                    "y": player["y"] - 35,
                    "vx": vx,
                    "vy": -speed,
                }
            )


def _update_bullets(state):
    active = []
    for bullet in state["bullets"]:
        if bullet.get("type") == "track":
            target = _nearest_enemy(state, bullet)
            if target:
                dx = target["x"] - bullet["x"]
                dy = target["y"] - bullet["y"]
                dist = max(1, (dx * dx + dy * dy) ** 0.5)
                speed = max(BULLET_SPEED, abs(bullet.get("vy", -BULLET_SPEED)))
                bullet["vx"] = dx / dist * speed
                bullet["vy"] = dy / dist * speed
        bullet["x"] += bullet["vx"]
        bullet["y"] += bullet["vy"]
        if -30 < bullet["y"] < SCREEN_HEIGHT + 30 and -30 < bullet["x"] < SCREEN_WIDTH + 30:
            active.append(bullet)
    state["bullets"] = active


def _nearest_enemy(state, bullet):
    targets = list(state["enemies"])
    if state.get("boss"):
        targets.append(state["boss"])
    if not targets:
        return None
    return min(
        targets,
        key=lambda target: (target["x"] - bullet["x"]) ** 2 + (target["y"] - bullet["y"]) ** 2,
    )


def _spawn_enemies(state):
    if state["boss"] or state["status"] == "boss_warning":
        return
    state["_enemy_timer"] += 1
    tier = _difficulty_tier(state)
    two_players = _alive_player_count(state) >= 2
    interval_table = [15, 13, 11, 9, 8, 7] if two_players else [26, 22, 18, 15, 13, 11]
    interval = interval_table[tier]
    if state["_enemy_timer"] < interval:
        return
    state["_enemy_timer"] = 0
    spawn_count_table = [2, 2, 3, 3, 4, 4] if two_players else [1, 1, 2, 2, 3, 3]
    spawn_count = spawn_count_table[tier]
    for _ in range(spawn_count):
        enemy_id = state["_next_enemy_id"]
        state["_next_enemy_id"] += 1
        enemy_type = _choose_enemy_type(tier)
        state["enemies"].append(
            {
                "id": "e{}".format(enemy_id),
                "type": enemy_type,
                "x": random.randint(40, SCREEN_WIDTH - 40),
                "y": -30,
                "hp": ENEMY_HP[enemy_type],
                "vy": ENEMY_SPEED + tier * 0.2 + (0.4 if two_players else 0),
                "shoot_timer": random.randint(0, 90),
            }
        )


def _difficulty_tier(state):
    score = state.get("score", 0)
    score_tier = 0
    for threshold in (80, 180, 360, 700, 1100):
        if score >= threshold:
            score_tier += 1
    time_tier = min(5, state.get("tick", 0) // 1800)
    return min(5, max(score_tier, time_tier))


def _choose_enemy_type(tier):
    if tier == 0:
        return random.choice([1, 1, 1, 2])
    weights = [
        [70, 25, 5],
        [55, 32, 13],
        [38, 38, 24],
        [24, 40, 36],
        [12, 36, 52],
        [6, 28, 66],
    ][tier]
    return random.choices([1, 2, 3], weights=weights, k=1)[0]


def _update_enemies(state):
    active = []
    for enemy in state["enemies"]:
        enemy["y"] += enemy["vy"]
        if enemy["y"] < SCREEN_HEIGHT + 40:
            active.append(enemy)
    state["enemies"] = active


def _update_dead_enemies(state):
    active = []
    for enemy in state["dead_enemies"]:
        enemy["death_timer"] += 1
        if enemy["death_timer"] < 36:
            active.append(enemy)
    state["dead_enemies"] = active


def _check_bullet_enemy_collisions(state):
    remaining_bullets = []
    hit_bullets = set()

    for bullet in state["bullets"]:
        hit_enemy = None
        for enemy in state["enemies"]:
            if _is_near(bullet, enemy, BULLET_HIT_RADIUS):
                hit_enemy = enemy
                break
        if hit_enemy:
            hit_bullets.add(bullet["id"])
            hit_enemy["hp"] -= 1
        else:
            remaining_bullets.append(bullet)

    remaining_enemies = []
    for enemy in state["enemies"]:
        if enemy["hp"] <= 0:
            state["score"] += ENEMY_SCORE.get(enemy["type"], 1)
            state["dead_enemies"].append(
                {
                    "id": "{}_dead_{}".format(enemy["id"], state["tick"]),
                    "type": enemy["type"],
                    "x": enemy["x"],
                    "y": enemy["y"],
                    "death_timer": 0,
                }
            )
            _spawn_gems(state, enemy)
            _spawn_power_item(state, enemy)
        else:
            remaining_enemies.append(enemy)

    state["bullets"] = [b for b in remaining_bullets if b["id"] not in hit_bullets]
    state["enemies"] = remaining_enemies


def _maybe_spawn_boss(state):
    if state["boss"] or state["boss_warning_timer"] > 0 or state["score"] < state["_boss_threshold"]:
        return
    state["status"] = "boss_warning"
    state["boss_warning_timer"] = BOSS_WARNING_TICKS


def _update_boss_warning(state):
    if state["status"] != "boss_warning":
        return
    state["boss_warning_timer"] = max(0, state["boss_warning_timer"] - 1)
    if state["boss_warning_timer"] > 0:
        return
    boss_hp = BOSS_BASE_HP + len(state["players"]) * BOSS_HP_PER_PLAYER
    state["boss"] = {
        "id": "boss1",
        "type": "crystal",
        "x": SCREEN_WIDTH // 2,
        "y": 90,
        "hp": boss_hp,
        "max_hp": boss_hp,
        "phase": 1,
        "invincible_timer": 30,
        "cloak_timer": 0,
        "visible": True,
        "active": True,
    }
    state["status"] = "playing"


def _spawn_boss_bullets(state):
    boss = state["boss"]
    if not boss:
        return
    _update_boss_cloak(state)
    state["_boss_shoot_timer"] += 1
    interval = 14 if boss.get("phase") == 2 else 20
    if state["_boss_shoot_timer"] < interval:
        _spawn_boss_phase_skills(state)
        return
    state["_boss_shoot_timer"] = 0
    velocities = (-3, -1, 1, 3) if boss.get("phase") == 2 else (-2, 0, 2)
    for vx in velocities:
        bullet_id = state["_next_boss_bullet_id"]
        state["_next_boss_bullet_id"] += 1
        state["boss_bullets"].append(
            {
                "id": "bb{}".format(bullet_id),
                "type": "boss_normal",
                "x": boss["x"],
                "y": boss["y"] + 50,
                "vx": vx,
                "vy": BOSS_BULLET_SPEED,
            }
        )
    _spawn_boss_phase_skills(state)


def _spawn_enemy_bullets(state):
    if not state["enemies"]:
        return
    for enemy in state["enemies"]:
        if enemy.get("type", 1) == 1 or enemy["y"] < 20:
            continue
        enemy["shoot_timer"] = enemy.get("shoot_timer", 0) + 1
        interval = 120 if enemy["type"] == 2 else 90
        if _alive_player_count(state) >= 2:
            interval = max(60, interval - 20)
        if enemy["shoot_timer"] < interval:
            continue
        enemy["shoot_timer"] = 0
        velocities = [(0, BOSS_BULLET_SPEED - 1)]
        if enemy["type"] == 3:
            velocities = [(-1.8, BOSS_BULLET_SPEED - 1), (0, BOSS_BULLET_SPEED), (1.8, BOSS_BULLET_SPEED - 1)]
        for vx, vy in velocities:
            bullet_id = state["_next_boss_bullet_id"]
            state["_next_boss_bullet_id"] += 1
            state["boss_bullets"].append(
                {
                    "id": "eb{}".format(bullet_id),
                    "type": "enemy_bullet",
                    "x": enemy["x"],
                    "y": enemy["y"] + 24,
                    "vx": vx,
                    "vy": vy,
                }
            )


def _update_boss_cloak(state):
    boss = state["boss"]
    if boss.get("phase") != 2:
        boss["visible"] = True
        return
    if boss.get("cloak_timer", 0) > 0:
        boss["visible"] = False
        boss["invincible_timer"] = max(boss.get("invincible_timer", 0), 2)
        if boss["cloak_timer"] == 1:
            boss["x"] = random.randint(70, SCREEN_WIDTH - 70)
            boss["y"] = random.randint(70, 170)
        return
    boss["visible"] = True
    state["_boss_cloak_timer"] += 1
    if state["_boss_cloak_timer"] >= BOSS_CLOAK_INTERVAL:
        state["_boss_cloak_timer"] = 0
        boss["cloak_timer"] = BOSS_CLOAK_TICKS


def _spawn_boss_phase_skills(state):
    boss = state["boss"]
    if boss.get("phase") != 2:
        return
    state["_boss_spiral_timer"] += 1
    state["_boss_burst_timer"] += 1
    if state["_boss_spiral_timer"] >= BOSS_SPIRAL_INTERVAL:
        state["_boss_spiral_timer"] = 0
        _spawn_spiral_bullets(state, boss)
    if state["_boss_burst_timer"] >= BOSS_BURST_INTERVAL:
        state["_boss_burst_timer"] = 0
        _spawn_burst_bullet(state, boss)


def _spawn_spiral_bullets(state, boss):
    for index in range(12):
        angle = index * 30 + (state["tick"] % 360)
        rad = angle * 3.1415926 / 180
        bullet_id = state["_next_boss_bullet_id"]
        state["_next_boss_bullet_id"] += 1
        state["boss_bullets"].append(
            {
                "id": "bb{}".format(bullet_id),
                "type": "boss_spiral",
                "x": boss["x"],
                "y": boss["y"] + 30,
                "vx": 3 * math.cos(rad),
                "vy": 3 * math.sin(rad),
            }
        )


def _spawn_burst_bullet(state, boss):
    target = _nearest_alive_player(state, boss)
    vx, vy = 0, BOSS_BULLET_SPEED
    if target:
        dx = target["x"] - boss["x"]
        dy = target["y"] - boss["y"]
        dist = max(1, (dx * dx + dy * dy) ** 0.5)
        vx = dx / dist * 3
        vy = dy / dist * 3
    bullet_id = state["_next_boss_bullet_id"]
    state["_next_boss_bullet_id"] += 1
    state["boss_bullets"].append(
        {
            "id": "bb{}".format(bullet_id),
            "type": "boss_burst",
            "x": boss["x"],
            "y": boss["y"] + 30,
            "vx": vx,
            "vy": vy,
        }
    )


def _update_boss_bullets(state):
    active = []
    for bullet in state["boss_bullets"]:
        bullet["x"] += bullet["vx"]
        bullet["y"] += bullet["vy"]
        if -30 < bullet["y"] < SCREEN_HEIGHT + 30:
            active.append(bullet)
    state["boss_bullets"] = active


def _check_bullet_boss_collisions(state):
    boss = state["boss"]
    if not boss:
        return

    remaining_bullets = []
    for bullet in state["bullets"]:
        if _is_near(bullet, boss, BOSS_HIT_RADIUS):
            if boss.get("invincible_timer", 0) > 0:
                remaining_bullets.append(bullet)
                continue
            boss["hp"] -= 1
        else:
            remaining_bullets.append(bullet)
    state["bullets"] = remaining_bullets

    if boss["hp"] <= boss["max_hp"] // 2 and boss.get("phase") == 1:
        boss["phase"] = 2
        boss["invincible_timer"] = BOSS_PHASE_INVINCIBLE_TICKS

    if boss["hp"] <= 0:
        state["score"] += BOSS_SCORE
        state["boss"] = None
        state["boss_bullets"] = []
        state["_boss_threshold"] += 100


def _is_near(a, b, radius):
    return abs(a["x"] - b["x"]) <= radius and abs(a["y"] - b["y"]) <= radius


def _spawn_gems(state, enemy):
    drops = ENEMY_GEM_DROP.get(enemy["type"], [(1, 0.5)])
    for gem_level, probability in drops:
        if random.random() > probability:
            continue
        item_id = state["_next_item_id"]
        state["_next_item_id"] += 1
        state["items"].append(
            {
                "id": "i{}".format(item_id),
                "type": "gem",
                "level": gem_level,
                "score": GEM_SCORE[gem_level],
                "x": enemy["x"] + random.randint(-16, 16),
                "y": enemy["y"] + random.randint(-12, 12),
                "vy": 3,
            }
        )


def _spawn_power_item(state, enemy):
    if random.random() > ITEM_DROP_RATE:
        return
    item_id = state["_next_item_id"]
    state["_next_item_id"] += 1
    item_type = random.choice(ITEM_TYPES)
    item = {
        "id": "i{}".format(item_id),
        "type": item_type,
        "x": enemy["x"] + random.randint(-12, 12),
        "y": enemy["y"] + random.randint(-12, 12),
        "vy": 2,
    }
    if item_type == "heal":
        item["amount"] = 3
    state["items"].append(item)


def _check_item_pickups(state):
    remaining_items = []
    players = list(state["players"].values())
    for item in state["items"]:
        picked = False
        for player in players:
            if not player["alive"]:
                continue
            if _is_near(player, item, ITEM_PICKUP_RADIUS):
                _apply_item(state, player, item)
                picked = True
                break
        if not picked:
            _move_item(state, item)
            if item["y"] < SCREEN_HEIGHT + 40:
                remaining_items.append(item)
    state["items"] = remaining_items


def _move_item(state, item):
    if item.get("type") == "gem":
        target = _nearest_alive_player(state, item)
        if target:
            dx = target["x"] - item["x"]
            dy = target["y"] - item["y"]
            dist = (dx * dx + dy * dy) ** 0.5
            if 0 < dist < GEM_MAGNET_RADIUS:
                item["x"] += dx / dist * GEM_MAGNET_SPEED
                item["y"] += dy / dist * GEM_MAGNET_SPEED
                return
    item["y"] += item.get("vy", 0)


def _nearest_alive_player(state, item):
    players = [p for p in state["players"].values() if p["alive"]]
    if not players:
        return None
    return min(
        players,
        key=lambda player: (player["x"] - item["x"]) ** 2 + (player["y"] - item["y"]) ** 2,
    )


def _apply_item(state, player, item):
    if item["type"] == "gem":
        state["score"] += item.get("score", 0)
    elif item["type"] == "heal":
        player["hp"] = min(10, player["hp"] + item.get("amount", 3))
    elif item["type"] == "shield":
        player["shield_timer"] = 180
    elif item["type"] == "upgrade":
        if player.get("power_level", 0) < 2:
            player["power_level"] = player.get("power_level", 0) + 1
        else:
            player["berserk_timer"] = BERSERK_DURATION
    elif item["type"] == "track":
        player["track_timer"] = TRACK_DURATION


def _alive_player_count(state):
    return sum(1 for player in state["players"].values() if player["alive"])


def _check_enemy_player_collisions(state):
    remaining_enemies = []
    for enemy in state["enemies"]:
        hit_player = None
        for player in state["players"].values():
            if player["alive"] and _is_near(enemy, player, PLAYER_HIT_RADIUS):
                hit_player = player
                break
        if hit_player:
            _damage_player(hit_player)
        else:
            remaining_enemies.append(enemy)
    state["enemies"] = remaining_enemies


def _check_boss_bullet_player_collisions(state):
    remaining_bullets = []
    for bullet in state["boss_bullets"]:
        hit_player = None
        for player in state["players"].values():
            if player["alive"] and _is_near(bullet, player, BOSS_BULLET_HIT_RADIUS):
                hit_player = player
                break
        if hit_player:
            _damage_player(hit_player)
        else:
            remaining_bullets.append(bullet)
    state["boss_bullets"] = remaining_bullets


def _damage_player(player):
    if player.get("shield_timer", 0) > 0:
        player["shield_timer"] = max(0, player["shield_timer"] - 60)
        return
    player["hp"] = max(0, player["hp"] - 1)
    player["damage_timer"] = 45
    if player["hp"] <= 0:
        player["alive"] = False
        player["death_timer"] = 1


def _check_game_over(state):
    if state["_settled"] or _alive_player_count(state) > 0:
        return

    _finish_game(state, "defeated")


def _check_time_limit(state):
    if state["_settled"]:
        return
    time_limit = state.get("time_limit_ticks")
    if time_limit and state["tick"] >= time_limit:
        _finish_game(state, "time_up")


def _finish_game(state, reason):
    state["status"] = "game_over"
    state["_settled"] = True
    state["end_reason"] = reason
    state["settlement"] = record_room_result(
        state["room_id"],
        list(state["players"].values()),
        state["score"],
        duration_sec=max(1, state["tick"] // 30),
    )


def public_state(state):
    return {
        "room_id": state["room_id"],
        "tick": state["tick"],
        "score": state["score"],
        "status": state["status"],
        "paused": state.get("paused", False),
        "pause_reason": state.get("pause_reason"),
        "time_limit_ticks": state.get("time_limit_ticks"),
        "remaining_ticks": max(0, state.get("time_limit_ticks", 0) - state["tick"]) if state.get("time_limit_ticks") else None,
        "end_reason": state.get("end_reason"),
        "boss_warning_timer": state.get("boss_warning_timer", 0),
        "players": list(state["players"].values()),
        "bullets": list(state["bullets"]),
        "boss_bullets": list(state["boss_bullets"]),
        "enemies": list(state["enemies"]),
        "dead_enemies": list(state["dead_enemies"]),
        "items": list(state["items"]),
        "boss": state["boss"],
        "settlement": state.get("settlement"),
    }

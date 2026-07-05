import unittest

from unittest.mock import patch

from db import get_connection, init_database
from game_engine import GAME_DURATION_TICKS, GAMES, create_game, reset_games, set_pause, step_game


class GameEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_database()

    def setUp(self):
        reset_games()

    def tearDown(self):
        reset_games()
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM rooms_history WHERE room_id = %s", ("123456",))
                cursor.execute("DELETE FROM scores WHERE room_id = %s", ("123456",))
                cursor.execute("DELETE FROM players WHERE id IN (%s, %s)", (1, 2))

    def make_room(self):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO players (id, name, token, is_online, last_login_at)
                    VALUES (1, 'engine_p1', 'engine_token_1', 1, NOW())
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        token = VALUES(token)
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO players (id, name, token, is_online, last_login_at)
                    VALUES (2, 'engine_p2', 'engine_token_2', 1, NOW())
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        token = VALUES(token)
                    """
                )
        return {
            "room_id": "123456",
            "players": [
                {"player_id": 1, "name": "p1"},
                {"player_id": 2, "name": "p2"},
            ],
        }

    @patch("game_engine.random.random", return_value=0.0)
    def test_bullet_kills_enemy_adds_score_and_spawns_gem(self, _random):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["bullets"].append(
            {
                "id": "b_test",
                "owner_id": 1,
                "type": "normal",
                "x": 100,
                "y": 100,
                "vx": 0,
                "vy": 0,
            }
        )
        state["enemies"].append(
            {"id": "e_test", "type": 1, "x": 100, "y": 100, "hp": 1, "vy": 0}
        )

        public = step_game("123456")

        self.assertEqual(public["score"], 1)
        self.assertEqual(public["bullets"], [])
        self.assertEqual(public["enemies"], [])
        self.assertEqual(len(public["dead_enemies"]), 1)
        self.assertEqual(public["dead_enemies"][0]["type"], 1)
        self.assertTrue(any(item["type"] == "gem" for item in public["items"]))

    def test_dead_enemy_animation_expires(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["dead_enemies"].append(
            {"id": "dead", "type": 1, "x": 100, "y": 100, "death_timer": 35}
        )

        public = step_game("123456")

        self.assertEqual(public["dead_enemies"], [])

    def test_bullet_damages_stronger_enemy_without_score(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["bullets"].append(
            {
                "id": "b_test",
                "owner_id": 1,
                "type": "normal",
                "x": 100,
                "y": 100,
                "vx": 0,
                "vy": 0,
            }
        )
        state["enemies"].append(
            {"id": "e_test", "type": 2, "x": 100, "y": 100, "hp": 3, "vy": 0}
        )

        public = step_game("123456")

        self.assertEqual(public["score"], 0)
        self.assertEqual(public["bullets"], [])
        self.assertEqual(len(public["enemies"]), 1)
        self.assertEqual(public["enemies"][0]["hp"], 2)

    @patch("game_engine.random.randint", return_value=100)
    @patch("game_engine.random.choice", return_value=1)
    def test_two_players_spawn_more_enemies(self, _choice, _randint):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["_enemy_timer"] = 14

        public = step_game("123456")

        self.assertEqual(len(public["enemies"]), 2)
        self.assertTrue(all(enemy["hp"] == 3 for enemy in public["enemies"]))

    @patch("game_engine.random.choices", return_value=[1])
    @patch("game_engine.random.randint", return_value=100)
    def test_late_game_spawns_even_more_enemies(self, _randint, _choices):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["_boss_threshold"] = 9999
        state["score"] = 400
        state["_enemy_timer"] = 8

        public = step_game("123456")

        self.assertEqual(len(public["enemies"]), 3)

    def test_game_ends_when_time_limit_reaches_five_minutes(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["tick"] = GAME_DURATION_TICKS - 1

        public = step_game("123456")

        self.assertEqual(public["status"], "game_over")
        self.assertEqual(public["end_reason"], "time_up")
        self.assertEqual(public["remaining_ticks"], 0)
        self.assertIn("settlement", public)

    def test_player_picks_up_gem_and_adds_score(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        state["players"]["2"]["alive"] = False
        state["items"].append(
            {
                "id": "i_test",
                "type": "gem",
                "level": 2,
                "score": 3,
                "x": player["x"],
                "y": player["y"],
                "vy": 0,
            }
        )

        public = step_game("123456")

        self.assertEqual(public["score"], 3)
        self.assertEqual(public["items"], [])

    def test_player_picks_up_heal(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        player["hp"] = 5
        state["items"].append(
            {
                "id": "i_heal",
                "type": "heal",
                "amount": 3,
                "x": player["x"],
                "y": player["y"],
                "vy": 0,
            }
        )

        public = step_game("123456")
        healed = [p for p in public["players"] if p["id"] == 1][0]

        self.assertEqual(healed["hp"], 8)
        self.assertEqual(public["items"], [])

    def test_upgrade_increases_bullet_count(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        state["players"]["2"]["alive"] = False
        state["items"].append(
            {
                "id": "i_upgrade",
                "type": "upgrade",
                "x": player["x"],
                "y": player["y"],
                "vy": 0,
            }
        )

        step_game("123456")
        state["_shoot_timer"] = 5
        public = step_game("123456")

        self.assertEqual(len(public["bullets"]), 2)

    def test_upgrade_at_max_starts_berserk(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        player["power_level"] = 2
        state["items"].append(
            {
                "id": "i_upgrade",
                "type": "upgrade",
                "x": player["x"],
                "y": player["y"],
                "vy": 0,
            }
        )

        public = step_game("123456")
        powered = [p for p in public["players"] if p["id"] == 1][0]

        self.assertGreater(powered["berserk_timer"], 0)

    def test_track_item_starts_tracking_bullets(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        state["players"]["2"]["alive"] = False
        state["items"].append(
            {
                "id": "i_track",
                "type": "track",
                "x": player["x"],
                "y": player["y"],
                "vy": 0,
            }
        )

        step_game("123456")
        state["_shoot_timer"] = 5
        public = step_game("123456")

        self.assertEqual(public["bullets"][0]["type"], "track")

    def test_berserk_spawns_five_bullets(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        state["players"]["2"]["alive"] = False
        player["berserk_timer"] = 100
        state["_shoot_timer"] = 5

        public = step_game("123456")

        self.assertEqual(len(public["bullets"]), 5)

    def test_gem_moves_toward_player_when_near(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        state["players"]["2"]["alive"] = False
        state["items"].append(
            {
                "id": "i_gem",
                "type": "gem",
                "level": 4,
                "score": 10,
                "x": player["x"] + 70,
                "y": player["y"],
                "vy": 3,
            }
        )

        public = step_game("123456")

        self.assertLess(public["items"][0]["x"], player["x"] + 70)

    def test_boss_spawns_when_score_reaches_threshold(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20

        public = step_game("123456")

        self.assertEqual(public["status"], "boss_warning")
        self.assertGreater(public["boss_warning_timer"], 0)
        for _ in range(60):
            public = step_game("123456")
        self.assertIsNotNone(public["boss"])
        self.assertEqual(public["boss"]["hp"], 160)
        self.assertEqual(public["boss"]["max_hp"], 160)
        self.assertGreater(public["boss"]["invincible_timer"], 0)

    def test_boss_warning_keeps_existing_enemies_and_bullets(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20
        state["enemies"].append({"id": "e_keep", "type": 1, "x": 200, "y": 100, "hp": 3, "vy": 0})
        state["bullets"].append(
            {
                "id": "b_keep",
                "owner_id": 1,
                "type": "normal",
                "x": 20,
                "y": 20,
                "vx": 0,
                "vy": -1,
            }
        )

        public = step_game("123456")

        self.assertEqual(public["status"], "boss_warning")
        self.assertEqual(len(public["enemies"]), 1)
        self.assertEqual(len(public["bullets"]), 1)

    def test_bullet_hits_and_defeats_boss(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20
        for _ in range(61):
            step_game("123456")
        state["boss"]["invincible_timer"] = 0
        state["items"] = []
        state["enemies"] = []
        state["score"] = 20
        state["boss"]["hp"] = 1
        state["bullets"].append(
            {
                "id": "b_boss",
                "owner_id": 1,
                "type": "normal",
                "x": state["boss"]["x"],
                "y": state["boss"]["y"],
                "vx": 0,
                "vy": 0,
            }
        )

        public = step_game("123456")

        self.assertIsNone(public["boss"])
        self.assertEqual(public["score"], 70)

    def test_boss_switches_to_phase_two_at_half_hp(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20
        for _ in range(61):
            step_game("123456")
        state["boss"]["invincible_timer"] = 0
        state["boss"]["hp"] = 50
        state["bullets"].append(
            {
                "id": "b_phase",
                "owner_id": 1,
                "type": "normal",
                "x": state["boss"]["x"],
                "y": state["boss"]["y"],
                "vx": 0,
                "vy": 0,
            }
        )

        public = step_game("123456")

        self.assertEqual(public["boss"]["phase"], 2)
        self.assertGreater(public["boss"]["invincible_timer"], 0)

    def test_boss_spawns_bullets(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20
        for _ in range(61):
            step_game("123456")
        state["_boss_shoot_timer"] = 19

        public = step_game("123456")

        self.assertEqual(len(public["boss_bullets"]), 3)

    def test_phase_two_boss_uses_spiral_and_burst(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20
        for _ in range(61):
            step_game("123456")
        state["boss"]["phase"] = 2
        state["_boss_spiral_timer"] = 149
        state["_boss_burst_timer"] = 239

        public = step_game("123456")
        bullet_types = {bullet["type"] for bullet in public["boss_bullets"]}

        self.assertIn("boss_spiral", bullet_types)
        self.assertIn("boss_burst", bullet_types)

    def test_phase_two_boss_can_cloak(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 20
        for _ in range(61):
            step_game("123456")
        state["boss"]["phase"] = 2
        state["_boss_cloak_timer"] = 359

        public = step_game("123456")

        self.assertGreater(public["boss"]["cloak_timer"], 0)

    def test_boss_bullet_damages_player(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        state["boss_bullets"].append(
            {
                "id": "bb_test",
                "type": "boss_normal",
                "x": player["x"],
                "y": player["y"],
                "vx": 0,
                "vy": 0,
            }
        )

        public = step_game("123456")
        damaged = [p for p in public["players"] if p["id"] == 1][0]

        self.assertEqual(damaged["hp"], 9)
        self.assertGreater(damaged["damage_timer"], 0)
        self.assertEqual(public["boss_bullets"], [])

    def test_player_death_sets_death_timer(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        player = state["players"]["1"]
        player["hp"] = 1
        state["boss_bullets"].append(
            {
                "id": "bb_test",
                "type": "boss_normal",
                "x": player["x"],
                "y": player["y"],
                "vx": 0,
                "vy": 0,
            }
        )

        public = step_game("123456")
        dead = [p for p in public["players"] if p["id"] == 1][0]

        self.assertFalse(dead["alive"])
        self.assertGreaterEqual(dead["death_timer"], 1)

    def test_auto_shield_unlocks_at_high_score(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 5000
        state["_auto_shield_timer"] = 1799

        public = step_game("123456")

        self.assertTrue(all(player["shield_timer"] > 0 for player in public["players"]))

    def test_enemy_collision_can_end_game_and_record_result(self):
        create_game(self.make_room())
        state = GAMES["123456"]
        state["score"] = 12
        for player in state["players"].values():
            player["hp"] = 1
            state["enemies"].append(
                {
                    "id": "e{}".format(player["id"]),
                    "type": 1,
                    "x": player["x"],
                    "y": player["y"],
                    "hp": 1,
                    "vy": 0,
                }
            )

        public = step_game("123456")

        self.assertEqual(public["status"], "game_over")
        self.assertIsNotNone(public["settlement"])
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT score FROM scores WHERE room_id = %s", ("123456",))
                score_row = cursor.fetchone()
                cursor.execute("SELECT score FROM rooms_history WHERE room_id = %s", ("123456",))
                history_row = cursor.fetchone()
        self.assertEqual(score_row["score"], 12)
        self.assertEqual(history_row["score"], 12)

    def test_paused_game_does_not_advance_tick(self):
        create_game(self.make_room())
        set_pause("123456", True, "test pause")

        public = step_game("123456")

        self.assertTrue(public["paused"])
        self.assertEqual(public["pause_reason"], "test pause")
        self.assertEqual(public["tick"], 0)

        public = set_pause("123456", False)
        self.assertFalse(public["paused"])
        self.assertIsNone(public["pause_reason"])


if __name__ == "__main__":
    unittest.main()

import unittest

import pygame

from online_game import (
    AudioState,
    fetch_rankings,
    game_over_button_at,
    get_asset,
    keys_to_input,
    pause_button_at,
    pause_menu_button_at,
    player_result_rows,
    rect_from_center,
)


class FakeKeys:
    def __init__(self, pressed):
        self.pressed = pressed

    def __getitem__(self, key):
        return key in self.pressed


class FakeSound:
    def __init__(self):
        self.plays = []
        self.stops = 0

    def play(self, loops=0):
        self.plays.append(loops)

    def stop(self):
        self.stops += 1


class FakeClient:
    def __init__(self, rankings=None, error=None):
        self.rankings = rankings or []
        self.error = error

    def get_rankings(self, mode="coop", limit=10):
        if self.error:
            raise self.error
        return self.rankings


class OnlineGameTest(unittest.TestCase):
    def test_keys_to_input(self):
        keys = FakeKeys({pygame.K_RIGHT, pygame.K_w})

        result = keys_to_input(keys)

        self.assertTrue(result["right"])
        self.assertTrue(result["up"])
        self.assertFalse(result["left"])
        self.assertFalse(result["down"])

    def test_rect_from_center(self):
        rect = rect_from_center({"x": 100, "y": 200}, 20, 40)

        self.assertEqual(rect.left, 90)
        self.assertEqual(rect.top, 180)
        self.assertEqual(rect.width, 20)
        self.assertEqual(rect.height, 40)

    def test_get_asset_selects_enemy_by_type(self):
        assets = {
            "enemy1": "e1",
            "enemy2": "e2",
            "enemy3": ["e3a", "e3b"],
            "enemy2_hit": "e2_hit",
        }

        self.assertEqual(get_asset(assets, "enemy", {"type": 2}), "e2")
        self.assertEqual(get_asset(assets, "enemy", {"type": 3}), "e3a")
        self.assertEqual(get_asset(assets, "enemy", {"type": 2, "hp": 4}), "e2_hit")

    def test_get_asset_selects_dead_enemy_animation(self):
        assets = {"enemy1_down": ["d1", "d2"]}

        self.assertEqual(
            get_asset(assets, "dead_enemy", {"type": 1, "death_timer": 6}),
            "d2",
        )

    def test_get_asset_selects_gem_by_level(self):
        assets = {"gem1": "g1", "gem2": "g2", "gem4": "g4"}

        self.assertEqual(get_asset(assets, "item", {"type": "gem", "level": 2}), "g2")
        self.assertEqual(get_asset(assets, "item", {"type": "gem", "level": 4}), "g4")

    def test_get_asset_selects_bullet_by_type(self):
        assets = {"bullet": ["b0", "b1", "b2", "b3"]}

        self.assertEqual(get_asset(assets, "bullet", {"type": "normal"}), "b0")
        self.assertEqual(get_asset(assets, "bullet", {"type": "berserk"}), "b1")
        self.assertEqual(get_asset(assets, "bullet", {"type": "track"}), "b3")

    def test_get_asset_selects_player_damage_and_death_frames(self):
        assets = {
            "players": ["normal"],
            "players_damaged": ["hurt1", "hurt2"],
            "players_death": ["dead1", "dead2"],
        }

        self.assertEqual(
            get_asset(assets, "player", {"alive": True, "damage_timer": 4}),
            "hurt2",
        )
        self.assertEqual(
            get_asset(assets, "player", {"alive": False, "death_timer": 8}),
            "dead2",
        )

    def test_get_asset_selects_power_item_icon(self):
        assets = {"heal": "heal_icon", "shield": "shield_icon", "upgrade": "upgrade_icon"}

        self.assertEqual(get_asset(assets, "item", {"type": "heal"}), "heal_icon")
        self.assertEqual(get_asset(assets, "item", {"type": "shield"}), "shield_icon")
        self.assertEqual(get_asset(assets, "item", {"type": "upgrade"}), "upgrade_icon")

    def test_audio_state_plays_warning_and_boss_music(self):
        audio = {key: FakeSound() for key in ("background", "boss", "warning")}
        state = AudioState()

        state.update(audio, {"status": "boss_warning"})
        state.update(audio, {"status": "playing", "boss": {"hp": 10}})

        self.assertEqual(audio["warning"].plays, [0])
        self.assertEqual(audio["boss"].plays, [-1])

    def test_audio_state_plays_delta_sounds(self):
        audio = {
            key: FakeSound()
            for key in (
                "background",
                "boss",
                "enemy_down",
                "crystal",
                "boom",
                "shield",
                "upgrade",
                "rush",
                "player_down",
            )
        }
        state = AudioState()
        state.update(
            audio,
            {
                "status": "playing",
                "items": [{"id": "gem"}],
                "players": [{"id": 1, "hp": 10, "alive": True, "shield_timer": 0, "power_level": 0}],
                "dead_enemies": [],
            },
        )
        state.update(
            audio,
            {
                "status": "playing",
                "items": [],
                "players": [
                    {
                        "id": 1,
                        "hp": 9,
                        "alive": False,
                        "shield_timer": 180,
                        "power_level": 1,
                        "berserk_timer": 10,
                    }
                ],
                "dead_enemies": [{"id": "e1_dead", "death_timer": 0}],
            },
        )

        self.assertEqual(audio["enemy_down"].plays, [0])
        self.assertEqual(audio["crystal"].plays, [0])
        self.assertEqual(audio["boom"].plays, [0])
        self.assertEqual(audio["player_down"].plays, [0])
        self.assertEqual(audio["shield"].plays, [0])
        self.assertEqual(audio["upgrade"].plays, [0])
        self.assertEqual(audio["rush"].plays, [0])

    def test_game_over_button_hit_detection(self):
        self.assertEqual(game_over_button_at((100, 530)), "again")
        self.assertEqual(game_over_button_at((220, 530)), "menu")
        self.assertEqual(game_over_button_at((360, 530)), "rankings")
        self.assertIsNone(game_over_button_at((20, 20)))

    def test_pause_button_hit_detection(self):
        self.assertTrue(pause_button_at((450, 24)))
        self.assertEqual(pause_menu_button_at((200, 335)), "resume")
        self.assertEqual(pause_menu_button_at((200, 400)), "menu")
        self.assertIsNone(pause_menu_button_at((20, 20)))

    def test_player_result_rows(self):
        rows = player_result_rows(
            {
                "players": [
                    {"name": "playerA", "hp": 3, "alive": True},
                    {"name": "playerB", "hp": 0, "alive": False},
                ]
            }
        )

        self.assertEqual(rows[0], "playerA  HP:3  ALIVE")
        self.assertEqual(rows[1], "playerB  HP:0  DOWN")

    def test_fetch_rankings_success_and_error(self):
        rankings, error = fetch_rankings(FakeClient(rankings=[{"rank": 1, "score": 100}]))
        self.assertEqual(rankings[0]["score"], 100)
        self.assertIsNone(error)

        rankings, error = fetch_rankings(FakeClient(error=RuntimeError("bad")))
        self.assertEqual(rankings, [])
        self.assertIn("bad", error)


if __name__ == "__main__":
    unittest.main()

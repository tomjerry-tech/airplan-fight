import sys
import types
import unittest
from unittest.mock import patch

import local_scores
from test import Game


class LocalScoresTest(unittest.TestCase):
    def setUp(self):
        self.old_modules = {
            name: sys.modules.get(name)
            for name in ("auth", "db", "rankings")
        }

    def tearDown(self):
        for name, module in self.old_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def install_fake_backend(self, login_error=None):
        auth = types.ModuleType("auth")
        db = types.ModuleType("db")
        rankings = types.ModuleType("rankings")

        auth.login_by_name = lambda name: (
            None,
            login_error,
        ) if login_error else ({"player_id": 7, "name": name}, None)
        db.init_database = lambda: None
        rankings.record_score = lambda player_id, score, mode="coop", room_id=None: 99

        sys.modules["auth"] = auth
        sys.modules["db"] = db
        sys.modules["rankings"] = rankings

    def test_submit_local_score_success(self):
        self.install_fake_backend()

        result = local_scores.submit_local_score(123, "single", "local_single")

        self.assertTrue(result["saved"])
        self.assertEqual(result["score_id"], 99)

    def test_submit_local_score_login_error(self):
        self.install_fake_backend({"error": "BAD_NAME"})

        result = local_scores.submit_local_score(123, "single", "bad")

        self.assertFalse(result["saved"])
        self.assertEqual(result["error"], "BAD_NAME")

    @patch("test.submit_local_score", return_value={"saved": True, "score_id": 1})
    def test_game_saves_score_once(self, submit):
        game = Game(mode="endless")
        game.score = 55

        first = game.save_local_score_once()
        second = game.save_local_score_once()

        self.assertEqual(first, second)
        submit.assert_called_once_with(55, "endless", "local_end")


if __name__ == "__main__":
    unittest.main()

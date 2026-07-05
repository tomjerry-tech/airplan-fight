import unittest
from unittest.mock import patch

from main_menu import (
    append_login_text,
    build_options,
    fetch_menu_rankings,
    launch_mode,
    option_at,
    set_backend_url,
    submit_login,
)


class MainMenuTest(unittest.TestCase):
    def test_build_options_contains_modes_and_rankings(self):
        options = build_options()

        self.assertEqual([option.key for option in options], ["single", "endless", "online", "rankings"])

    def test_option_at_returns_clicked_mode(self):
        options = build_options()
        first = options[0]

        self.assertEqual(option_at(options, first.rect.center), "single")
        self.assertIsNone(option_at(options, (0, 0)))

    @patch("main_menu.ensure_backend", return_value=True)
    @patch("main_menu.subprocess.Popen")
    def test_launch_online_uses_online_game(self, popen, _ensure_backend):
        set_backend_url("http://8.137.125.43:5000")
        launch_mode("online")

        self.assertIn("online_game.py", str(popen.call_args[0][0][1]))
        self.assertIn("--server", popen.call_args[0][0])
        self.assertIn("http://8.137.125.43:5000", popen.call_args[0][0])
        set_backend_url("http://127.0.0.1:5000")

    @patch("main_menu.subprocess.Popen")
    def test_launch_single_uses_local_game(self, popen):
        launch_mode("single")

        self.assertIn("test.py", str(popen.call_args[0][0][1]))
        self.assertIn("--mode", popen.call_args[0][0])
        self.assertIn("single", popen.call_args[0][0])

    @patch("main_menu.subprocess.Popen")
    def test_launch_endless_uses_endless_mode(self, popen):
        launch_mode("endless")

        self.assertIn("test.py", str(popen.call_args[0][0][1]))
        self.assertIn("--mode", popen.call_args[0][0])
        self.assertIn("endless", popen.call_args[0][0])

    @patch("main_menu.ensure_backend", return_value=False)
    def test_fetch_rankings_returns_error_when_backend_down(self, _ensure_backend):
        rows, error = fetch_menu_rankings("single")

        self.assertEqual(rows, [])
        self.assertIsNotNone(error)

    def test_append_login_text_keeps_valid_name_chars(self):
        self.assertEqual(append_login_text("ab", " 测试-12_"), "ab测试12_")

    @patch("main_menu.login_player", return_value={"player_id": 1, "name": "player1", "token": "t"})
    def test_submit_login_uses_default_name_when_empty(self, login_player):
        name, player = submit_login("")

        self.assertRegex(name, r"^player\d{1,4}$")
        self.assertEqual(player["player_id"], 1)
        login_player.assert_called_once_with(name)


if __name__ == "__main__":
    unittest.main()

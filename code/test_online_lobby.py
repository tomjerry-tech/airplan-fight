import unittest

import pygame

from online_lobby import (
    LobbyState,
    STATE_JOIN,
    STATE_MENU,
    STATE_RANKINGS,
    STATE_STARTING,
    STATE_WAITING,
    append_name_text,
    button_rects,
    handle_lobby_event,
)


class OnlineLobbyTest(unittest.TestCase):
    def key(self, key, unicode=""):
        return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)

    def click(self, pos):
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)

    def test_name_submit_moves_to_menu(self):
        lobby = LobbyState()
        lobby.handle_text("ab")

        action = handle_lobby_event(lobby, self.key(pygame.K_RETURN))

        self.assertEqual(action, "login")
        self.assertEqual(lobby.state, STATE_MENU)

    def test_append_name_text_keeps_valid_name_chars(self):
        self.assertEqual(append_name_text("ab", " 测试-12_"), "ab测试12_")

    def test_menu_create_action(self):
        lobby = LobbyState()
        lobby.name = "ab"
        lobby.state = STATE_MENU

        action = handle_lobby_event(lobby, self.key(pygame.K_c, "c"))

        self.assertEqual(action, "create")
        self.assertEqual(lobby.state, STATE_WAITING)

    def test_mouse_create_action(self):
        lobby = LobbyState()
        lobby.name = "ab"
        lobby.state = STATE_MENU

        action = handle_lobby_event(lobby, self.click(button_rects()["create"].center))

        self.assertEqual(action, "create")
        self.assertEqual(lobby.state, STATE_WAITING)

    def test_mouse_submit_name_action(self):
        lobby = LobbyState()
        lobby.handle_text("ab")

        action = handle_lobby_event(lobby, self.click(button_rects()["submit_name"].center))

        self.assertEqual(action, "login")
        self.assertEqual(lobby.state, STATE_MENU)

    def test_join_flow(self):
        lobby = LobbyState()
        lobby.state = STATE_MENU
        handle_lobby_event(lobby, self.key(pygame.K_j, "j"))
        lobby.handle_text("1234")

        action = handle_lobby_event(lobby, self.key(pygame.K_RETURN))

        self.assertEqual(lobby.state, STATE_WAITING)
        self.assertEqual(lobby.room_id, "1234")
        self.assertEqual(action, "join")

    def test_join_key_enters_join_state(self):
        lobby = LobbyState()
        lobby.state = STATE_MENU

        handle_lobby_event(lobby, self.key(pygame.K_j, "j"))

        self.assertEqual(lobby.state, STATE_JOIN)

    def test_mouse_join_enters_join_state(self):
        lobby = LobbyState()
        lobby.state = STATE_MENU

        handle_lobby_event(lobby, self.click(button_rects()["join"].center))

        self.assertEqual(lobby.state, STATE_JOIN)

    def test_mouse_rankings_action(self):
        lobby = LobbyState()
        lobby.state = STATE_MENU

        action = handle_lobby_event(lobby, self.click(button_rects()["rankings"].center))

        self.assertEqual(action, "rankings")
        self.assertEqual(lobby.state, STATE_MENU)

    def test_rankings_key_action(self):
        lobby = LobbyState()
        lobby.state = STATE_MENU

        action = handle_lobby_event(lobby, self.key(pygame.K_r, "r"))

        self.assertEqual(action, "rankings")

    def test_show_rankings_and_back_to_menu(self):
        lobby = LobbyState()
        lobby.show_rankings([{"rank": 1, "name": "abc", "score": 100}])

        self.assertEqual(lobby.state, STATE_RANKINGS)
        self.assertEqual(lobby.rankings[0]["score"], 100)

        handle_lobby_event(lobby, self.key(pygame.K_ESCAPE))

        self.assertEqual(lobby.state, STATE_MENU)

    def test_rankings_back_button_returns_menu(self):
        lobby = LobbyState()
        lobby.show_rankings([])

        handle_lobby_event(lobby, self.click(button_rects()["rankings_back"].center))

        self.assertEqual(lobby.state, STATE_MENU)

    def test_join_requires_four_digits(self):
        lobby = LobbyState()
        lobby.state = STATE_JOIN
        lobby.handle_text("123")

        action = handle_lobby_event(lobby, self.key(pygame.K_RETURN))

        self.assertIsNone(action)
        self.assertEqual(lobby.state, STATE_JOIN)
        self.assertEqual(lobby.message, "Room id must be 4 digits")

    def test_room_update_moves_to_starting_when_ready(self):
        lobby = LobbyState()
        lobby.state = STATE_WAITING

        lobby.apply_room_update(
            {
                "room_id": "1234",
                "status": "ready",
                "players": [{"name": "a"}, {"name": "b"}],
            }
        )

        self.assertEqual(lobby.state, STATE_STARTING)
        self.assertEqual(lobby.room_id, "1234")
        self.assertEqual(len(lobby.players), 2)


if __name__ == "__main__":
    unittest.main()

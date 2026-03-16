import unittest
from game.game_manager import GameManager


class TestGameManager(unittest.TestCase):

    def setUp(self):
        """Create a fresh GameManager before each test"""
        self.game = GameManager("ABCD")

    # --- add_player ---

    def test_add_player_succeeds(self):
        result = self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.assertTrue(result)
        self.assertIn(1, self.game._players)

    def test_add_second_player_succeeds(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        result = self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.assertTrue(result)

    def test_add_third_player_rejected(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        result = self.game.add_player(user_id=3, sid="sid3", username="charlie")
        self.assertFalse(result)
        self.assertEqual(len(self.game._players), 2)

    def test_add_duplicate_player_updates_sid(self):
        self.game.add_player(user_id=1, sid="old_sid", username="alice")
        result = self.game.add_player(user_id=1, sid="new_sid", username="alice")
        self.assertFalse(result)  # returns False for duplicate
        self.assertEqual(self.game._players[1].sid, "new_sid")  # but sid is updated

    # --- all_players_ready ---

    def test_all_players_ready_false_with_one_player(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.assertFalse(self.game.all_players_ready())

    def test_all_players_ready_true_with_two_players(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.assertTrue(self.game.all_players_ready())

    # --- mark_ready / all_ready / can_start ---

    def test_can_start_false_if_not_all_ready(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.mark_ready(1)
        self.assertFalse(self.game.can_start())

    def test_can_start_true_when_both_ready(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.game.mark_ready(1)
        self.game.mark_ready(2)
        self.assertTrue(self.game.can_start())

    def test_can_start_false_if_already_started(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.game.mark_ready(1)
        self.game.mark_ready(2)
        self.game.start_game()
        self.assertFalse(self.game.can_start())

    # --- check_winner ---

    def test_check_winner_no_winner_when_close(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.game._players[1].distance_travelled = 200
        self.game._players[2].distance_travelled = 100  # gap = 100, under 300
        won, winner_id, reason = self.game.check_winner()
        self.assertFalse(won)

    def test_check_winner_returns_winner_at_threshold(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.game._players[1].distance_travelled = 400
        self.game._players[2].distance_travelled = 100  # gap = 300, exactly at threshold
        won, winner_id, reason = self.game.check_winner()
        self.assertTrue(won)
        self.assertEqual(winner_id, 1)

    # --- get_chunk / caching ---

    def test_get_chunk_returns_a_chunk(self):
        chunk = self.game.get_chunk(0)
        self.assertIsNotNone(chunk)

    def test_get_chunk_caches_result(self):
        chunk1 = self.game.get_chunk(0)
        chunk2 = self.game.get_chunk(0)
        self.assertIs(chunk1, chunk2)  # same object from cache

    # --- update_sid ---

    def test_update_sid_returns_true_for_valid_user(self):
        self.game.add_player(user_id=1, sid="old", username="alice")
        result = self.game.update_sid(1, "new_sid")
        self.assertTrue(result)
        self.assertEqual(self.game._players[1].sid, "new_sid")

    def test_update_sid_returns_false_for_unknown_user(self):
        result = self.game.update_sid(99, "new_sid")
        self.assertFalse(result)

    # --- get_opponent ---

    def test_get_opponent_user_id(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.assertEqual(self.game.get_opponent_user_id(1), 2)
        self.assertEqual(self.game.get_opponent_user_id(2), 1)

    def test_get_opponent_username(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.game.add_player(user_id=2, sid="sid2", username="bob")
        self.assertEqual(self.game.get_opponent_username(1), "bob")

    def test_get_opponent_returns_none_with_one_player(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.assertIsNone(self.game.get_opponent_user_id(1))

    # --- is_over ---

    def test_is_over_false_by_default(self):
        self.assertFalse(self.game.is_over())

    def test_is_over_true_after_opponent_left(self):
        self.game.end_game(winner_user_id=1, reason="opponent_left")
        self.assertTrue(self.game.is_over())

    # --- get_player_username ---

    def test_get_player_username_returns_correct_name(self):
        self.game.add_player(user_id=1, sid="sid1", username="alice")
        self.assertEqual(self.game.get_player_username(1), "alice")

    def test_get_player_username_returns_none_for_unknown(self):
        self.assertIsNone(self.game.get_player_username(99))


if __name__ == '__main__':
    unittest.main()
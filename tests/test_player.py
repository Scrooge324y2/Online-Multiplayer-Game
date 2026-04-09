import unittest
from game.player import Player


class TestPlayer(unittest.TestCase):

    def setUp(self):
        """Create a fresh player before each test"""
        self.player = Player(user_id=1, sid="abc123", username="testuser")

    # --- update_position ---

    def test_update_position_changes_x_and_y(self):
        self.player.update_position(200, 300)
        self.assertEqual(self.player.x, 200)
        self.assertEqual(self.player.y, 300)

    def test_update_position_to_zero(self):
        self.player.update_position(0, 0)
        self.assertEqual(self.player.x, 0)
        self.assertEqual(self.player.y, 0)

    # --- update_distance ---

    def test_update_distance_increases_when_moving_forward(self):
        self.player.update_distance(500)
        self.assertEqual(self.player.distance_travelled, 500)

    def test_update_distance_does_not_decrease(self):
        self.player.update_distance(500)
        self.player.update_distance(100)  # moving backwards - should be ignored
        self.assertEqual(self.player.distance_travelled, 500)

    def test_update_distance_same_value_unchanged(self):
        self.player.update_distance(100)
        self.player.update_distance(100)
        self.assertEqual(self.player.distance_travelled, 100)

    # --- update_sid ---

    def test_update_sid_changes_sid(self):
        self.player.update_sid("new_sid_456")
        self.assertEqual(self.player.sid, "new_sid_456")

    # --- to_dict ---

    def test_to_dict_contains_correct_keys(self):
        result = self.player.to_dict()
        self.assertIn('user_id', result)
        self.assertIn('username', result)
        self.assertIn('x', result)
        self.assertIn('y', result)

    def test_to_dict_contains_correct_values(self):
        result = self.player.to_dict()
        self.assertEqual(result['user_id'], 1)
        self.assertEqual(result['username'], "testuser")

    def test_to_dict_reflects_updated_position(self):
        self.player.update_position(999, 888)
        result = self.player.to_dict()
        self.assertEqual(result['x'], 999)
        self.assertEqual(result['y'], 888)


if __name__ == '__main__':
    unittest.main()
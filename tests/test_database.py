import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

test_engine = create_engine('sqlite:///:memory:', echo=False)
TestSession = sessionmaker(bind=test_engine)
test_session = TestSession()

import database

database.engine = test_engine
database.session = test_session

from database import Base, User, Game, UserGame
Base.metadata.create_all(test_engine)


class TestUserModel(unittest.TestCase):

    def setUp(self):
        """Wipe all tables before each test for a clean state"""
        test_session.query(UserGame).delete()
        test_session.query(Game).delete()
        test_session.query(User).delete()
        test_session.commit()

    # --- add_user ---

    def test_add_user_returns_true(self):
        result = User.add_user("alice", "password123")
        self.assertTrue(result)

    def test_add_user_persists_to_db(self):
        User.add_user("alice", "password123")
        user = test_session.query(User).filter_by(Username="alice").first()
        self.assertIsNotNone(user)

    # --- validate_username ---

    def test_validate_username_true_for_new_name(self):
        self.assertTrue(User.validate_username("brandnew"))

    def test_validate_username_false_for_existing_name(self):
        User.add_user("alice", "password123")
        self.assertFalse(User.validate_username("alice"))

    # --- authenticate_user ---

    def test_authenticate_user_correct_password(self):
        User.add_user("alice", "password123")
        self.assertTrue(User.authenticate_user("alice", "password123"))

    def test_authenticate_user_wrong_password(self):
        User.add_user("alice", "password123")
        self.assertFalse(User.authenticate_user("alice", "wrongpassword"))

    def test_authenticate_user_nonexistent_user(self):
        self.assertFalse(User.authenticate_user("ghost", "password123"))

    # --- get_user_id ---

    def test_get_user_id_returns_id(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        self.assertIsNotNone(user_id)
        self.assertIsInstance(user_id, int)

    def test_get_user_id_returns_none_for_unknown(self):
        result = User.get_user_id("nobody")
        self.assertIsNone(result)

    # --- change_password ---

    def test_change_password_allows_login_with_new_password(self):
        User.add_user("alice", "old_pass")
        user_id = User.get_user_id("alice")
        User.change_password(user_id, "new_pass")
        self.assertTrue(User.authenticate_user("alice", "new_pass"))
        self.assertFalse(User.authenticate_user("alice", "old_pass"))

    # --- change_username ---

    def test_change_username_updates_name(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        User.change_username(user_id, "alice2")
        self.assertIsNotNone(User.get_user_id("alice2"))
        self.assertIsNone(User.get_user_id("alice"))

    # --- deactivate_user ---

    def test_deactivate_user_returns_true(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        result = User.deactivate_user(user_id)
        self.assertTrue(result)

    def test_deactivate_user_changes_username(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        User.deactivate_user(user_id)
        user = test_session.get(User, user_id)
        self.assertTrue(user.Username.startswith("Deactivated_User"))

    # --- get_win_rate ---

    def test_get_win_rate_zero_with_no_games(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        self.assertEqual(User.get_win_rate(user_id), 0.0)

    # --- create_recovery_key ---

    def test_create_recovery_key_returns_string(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        key = User.create_recovery_key(user_id)
        self.assertIsNotNone(key)
        self.assertIsInstance(key, str)

    def test_create_recovery_key_not_duplicated(self):
        """Second call without new_key=True should return None (key already exists)"""
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        User.create_recovery_key(user_id)
        second_call = User.create_recovery_key(user_id)
        self.assertIsNone(second_call)

    def test_authenticate_recovery_key_correct(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        key = User.create_recovery_key(user_id)
        self.assertTrue(User.authenticate_recovery_key(user_id, key))

    def test_authenticate_recovery_key_wrong(self):
        User.add_user("alice", "password123")
        user_id = User.get_user_id("alice")
        User.create_recovery_key(user_id)
        self.assertFalse(User.authenticate_recovery_key(user_id, "wrongkey"))


if __name__ == '__main__':
    unittest.main()
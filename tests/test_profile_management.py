from database import User


class TestChangePassword:

    def test_change_password_success(self, logged_in_client, registered_user):
        resp = logged_in_client.post(
            "/change_password",
            data={
                "current_password": registered_user["password"],
                "new_password": "NewPass999",
                "confirm_password": "NewPass999",
            },
            follow_redirects=True,
        )
        assert b"Password changed successfully" in resp.data
        assert User.authenticate_user(registered_user["username"], "NewPass999")

    def test_change_password_wrong_current_password(self, logged_in_client, registered_user):
        resp = logged_in_client.post(
            "/change_password",
            data={
                "current_password": "wrong",
                "new_password": "NewPass999",
                "confirm_password": "NewPass999",
            },
            follow_redirects=True,
        )
        assert b"Current password is incorrect" in resp.data

    def test_change_password_mismatch_confirmation(self, logged_in_client, registered_user):
        resp = logged_in_client.post(
            "/change_password",
            data={
                "current_password": registered_user["password"],
                "new_password": "NewPass999",
                "confirm_password": "DifferentPass",
            },
            follow_redirects=True,
        )
        assert b"do not match" in resp.data

    def test_change_password_requires_login(self, client):
        """Unauthenticated users should be redirected to login."""
        resp = client.post(
            "/change_password",
            data={"current_password": "x", "new_password": "y", "confirm_password": "y"},
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_get_change_password_page_returns_200(self, logged_in_client):
        assert logged_in_client.get("/change_password").status_code == 200


class TestChangeUsername:

    def test_change_username_success(self, logged_in_client):
        resp = logged_in_client.post(
            "/change_username",
            data={"new_username": "newname"},
            follow_redirects=True,
        )
        assert b"Username changed successfully" in resp.data
        # Session should reflect the new username
        with logged_in_client.session_transaction() as sess:
            assert sess.get("username") == "newname"

    def test_change_username_to_existing_username(self, client, registered_user):
        """Changing to a username already taken should flash an error."""
        # Register a second user
        client.post("/register", data={"username": "other", "password": "pass"})
        # Log in as testuser
        client.post("/login", data=registered_user)
        resp = client.post(
            "/change_username",
            data={"new_username": "other"},
            follow_redirects=True,
        )
        assert b"already in use" in resp.data

    def test_change_username_empty_value(self, logged_in_client):
        resp = logged_in_client.post(
            "/change_username",
            data={"new_username": ""},
            follow_redirects=True,
        )
        assert b"cannot be empty" in resp.data

    def test_change_username_requires_login(self, client):
        resp = client.post("/change_username", data={"new_username": "x"})
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_get_change_username_page_returns_200(self, logged_in_client):
        assert logged_in_client.get("/change_username").status_code == 200


class TestDeleteAccount:

    def test_delete_account_success(self, logged_in_client, registered_user):
        resp = logged_in_client.post(
            "/delete_account",
            data={"password": registered_user["password"]},
            follow_redirects=True,
        )
        assert b"Account deleted successfully" in resp.data
        # Session should be cleared
        with logged_in_client.session_transaction() as sess:
            assert "username" not in sess

    def test_delete_account_wrong_password(self, logged_in_client, registered_user):
        resp = logged_in_client.post(
            "/delete_account",
            data={"password": "wrong"},
            follow_redirects=True,
        )
        assert b"Password is incorrect" in resp.data

    def test_delete_account_empty_password(self, logged_in_client):
        resp = logged_in_client.post(
            "/delete_account",
            data={"password": ""},
            follow_redirects=True,
        )
        assert b"required" in resp.data

    def test_delete_account_requires_login(self, client):
        resp = client.post("/delete_account", data={"password": "x"})
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_get_delete_account_page_returns_200(self, logged_in_client):
        assert logged_in_client.get("/delete_account").status_code == 200



class TestRecoveryKey:

    def test_recovery_key_page_shows_key_from_session(self, logged_in_client):
        """If a recovery key is stored in session, the page should display it."""
        with logged_in_client.session_transaction() as sess:
            sess["recovery_key"] = "TEST-RECOVERY-KEY-123"
        resp = logged_in_client.get("/recovery_key", follow_redirects=True)
        assert b"TEST-RECOVERY-KEY-123" in resp.data

    def test_recovery_key_page_redirects_without_key_in_session(self, logged_in_client):
        """Without a key in session, should redirect (to menu)."""
        resp = logged_in_client.get("/recovery_key")
        assert resp.status_code == 302

    def test_recovery_key_consumed_after_view(self, logged_in_client):
        """The key should be popped from session after being displayed once."""
        with logged_in_client.session_transaction() as sess:
            sess["recovery_key"] = "ONE-TIME-KEY"
        logged_in_client.get("/recovery_key")
        with logged_in_client.session_transaction() as sess:
            assert "recovery_key" not in sess

    def test_new_recovery_key_success(self, logged_in_client, registered_user):
        resp = logged_in_client.post(
            "/new_recovery_key",
            data={"password": registered_user["password"]},
            follow_redirects=True,
        )
        # Should redirect to the recovery key display page
        assert resp.status_code == 200

    def test_new_recovery_key_wrong_password(self, logged_in_client):
        resp = logged_in_client.post(
            "/new_recovery_key",
            data={"password": "wrong"},
            follow_redirects=True,
        )
        assert b"Password is incorrect" in resp.data

    def test_new_recovery_key_empty_password(self, logged_in_client):
        resp = logged_in_client.post(
            "/new_recovery_key",
            data={"password": ""},
            follow_redirects=True,
        )
        assert b"required" in resp.data

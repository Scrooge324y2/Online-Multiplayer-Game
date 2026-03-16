"""
Shared pytest fixtures for the NEA integration test suite.

Uses an in-memory SQLite database so tests never touch database.db.
All fixtures are function-scoped – each test gets a clean slate.
"""
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ── Build a fresh in-memory engine & session ──────────────────────────────────
from database import Base          # import Base *before* patching session

TEST_ENGINE = create_engine("sqlite:///:memory:", echo=False)
TestSession = sessionmaker(bind=TEST_ENGINE)
test_session = TestSession()

# Patch the module-level session used by all model static methods
# Must happen before 'app' is imported so every reference to database.session
# resolves to our test session.
import database as db_module
db_module.session = test_session
db_module.engine  = TEST_ENGINE

# Create all tables in the in-memory DB
Base.metadata.create_all(TEST_ENGINE)

# ── Now import the Flask app (it will pick up the patched session) ─────────────
from app import app as flask_app, games


@pytest.fixture(autouse=True)
def clean_db():
    """Drop and recreate all tables before every test."""
    Base.metadata.drop_all(TEST_ENGINE)
    Base.metadata.create_all(TEST_ENGINE)
    games.clear()                     # also wipe in-memory game state
    yield
    test_session.rollback()


@pytest.fixture()
def client():
    """Flask test client with sessions enabled."""
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as c:
        yield c


@pytest.fixture()
def registered_user(client):
    """Register a user and return their credentials."""
    credentials = {"username": "testuser", "password": "Password123"}
    client.post("/register", data=credentials, follow_redirects=True)
    return credentials


@pytest.fixture()
def logged_in_client(client, registered_user):
    """A test client that is already logged in."""
    client.post("/login", data=registered_user, follow_redirects=True)
    return client
# Endless Racer

A real-time 2-player racing game for the browser. Both players run the same
procedurally generated course, and the first to pull 200 tiles ahead of their
opponent wins.

## Features

- **Real-time multiplayer** with Flask-SocketIO: per-room game state, live
  opponent positions, a live "metres ahead/behind" HUD, and reconnection
  handling.
- **Private lobbies and quick match**: share a 4-letter game code, or join the
  matchmaking queue.
- **Procedural maps**: OpenSimplex noise with four biomes (Plain, Hill,
  Mountain, Cave) and difficulty that scales as you run. Maps are generated
  server-side from a per-game seed and cached, so both players see identical
  terrain. Each chunk is checked with a BFS traversability test, with a
  flat-chunk fallback.
- **Win and forfeit detection** on the server, including opponent disconnects.
- **Accounts**: bcrypt password hashing, one-time recovery keys, and
  session-based access control. Users can change their username and password
  or delete their account.
- **Stats**: leaderboard (top 10 by wins), win rate, and match history.
- **Tests**: unit and integration tests with unittest and pytest, using an
  in-memory SQLite database.

## Tech stack

Python, Flask, Flask-SocketIO, SQLAlchemy (SQLite), Phaser 3, Bootstrap 5,
OpenSimplex, bcrypt

## Controls

| Key | Action |
|-----|--------|
| Up | Jump (double jump in mid-air, wall jump on walls) |
| Left / Right | Slow down / speed up |
| Down | Fast fall |

Spikes slow you down, so dodge them.

## Running locally

```bash
git clone <your-repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install flask flask-socketio sqlalchemy bcrypt opensimplex python-dotenv
cp .env.example .env             # then set SECRET_KEY
python app.py
```

Open http://localhost:5000, register two accounts in separate browsers, and
start a game.

## Tests

```bash
pip install pytest
pytest tests/
```

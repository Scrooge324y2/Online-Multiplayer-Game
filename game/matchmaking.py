import time
import random
import string


class MatchmakingQueue:
    def __init__(self):
        self._queue = []  # List of waiting players
        self._player_data = {}  # Store player info {sid: {username, join_time, etc}}

    def add_player(self, sid, username=None):
        """Add a player to the matchmaking queue"""
        if sid not in [p['sid'] for p in self._queue]:
            player_info = {
                'sid': sid,
                'username': username,
                'join_time': time.time()
            }
            self._queue.append(player_info)
            self._player_data[sid] = player_info
            return True
        return False

    def remove_player(self, sid):
        self._queue = [p for p in self._queue if p['sid'] != sid]
        if sid in self._player_data:
            del self._player_data[sid]

    def find_match(self):
        if len(self._queue) >= 2:
            player1 = self._queue.pop(0)
            player2 = self._queue.pop(0)

            # Clean up player data
            self._player_data.pop(player1['sid'], None)
            self._player_data.pop(player2['sid'], None)

            return player1, player2
        return None

    def get_queue_size(self):
        return len(self._queue)

    def is_player_in_queue(self, sid):
        return sid in self._player_data

    def generate_game_code(self):
        return ''.join(random.choices(string.ascii_uppercase, k=4))

    def get_queue(self):
        return self._queue
from game.logic import generate_chunk
import random
import time

class GameManager:
    def __init__(self, code):
        self._max_players = 2
        self._player_usernames = {}
        self._players = {}
        self._game_started = False
        self._chunk_cache = []
        self._room_code = code
        self._random_seed = random.randint(1, 10000)
        self._start_time = 0
        self._end_time = 0
        self._winner = None
        self._win_distance = 300
        self._game_duration = 180
        self._player_distances = {}


    def add_player(self, sid):
        if len(self._players) >= self._max_players:
            return False
        self._players[sid] = {'id': sid, 'x': 100, 'y': 450}
        return True

    def remove_player(self, sid):
        if sid in self._players:
            del self._players[sid]
        if len(self._players) < self._max_players:
            self._game_started = False

    def all_players_ready(self):
        return len(self._players) == self._max_players

    def update_position(self, sid, x, y):
        if sid in self._players:
            self._players[sid]['x'] = x
            self._players[sid]['y'] = y
            return self._players[sid]
        return None

    def get_chunk(self, offset):
        if offset < len(self._chunk_cache):
            return self._chunk_cache[offset]
        else:
            chunk = generate_chunk(offset=offset, seed=self._random_seed)
            self._chunk_cache.append(chunk)
            return chunk

    def update_sid(self, old_sid, new_sid):#updates a player's socket ID wghen they reconnect
        if old_sid in self._players:
            # Get the player data
            player_data = self._players.pop(old_sid)
            # Update the ID field
            player_data['id'] = new_sid
            # Store with new socket ID as key
            self._players[new_sid] = player_data
            print(f"  Successfully updated player: {old_sid} to {new_sid}")
            return True
        else:
            print(f"  Warning: old_sid {old_sid} not found in players")
            print(f"  Current players: {list(self._players.keys())}")
            return False

    def update_distance(self, sid, new_x):
        if sid not in self._player_distances:
            self._player_distances[sid] = 0

        if sid in self._players:
            old_x = self._players[sid].get('furthest_x', 100)
            if new_x > old_x: #only update if player moved forwards
                self._player_distances[sid] = new_x
                self._players[sid]['furthest_x'] = new_x

    def get_distance_between_players(self):
        if len(self._player_distances) < 2:
            return 0

        player_sids = list(self._player_distances.keys())
        print(f"distance between players: {self._player_distances[player_sids[0]] - self._player_distances[player_sids[1]]}")
        return abs(self._player_distances[player_sids[0]] - self._player_distances[player_sids[1]])

    def get_leading_player(self):
        if len(self._player_distances) < 2:
            return None

        player_sids = list(self._player_distances.keys())
        p1_distance = self._player_distances[player_sids[0]]
        p2_distance = self._player_distances[player_sids[1]]

        if p1_distance > p2_distance:
            return player_sids[0]
        elif p2_distance > p1_distance:
            return player_sids[1]
        else:
            return None

    def check_winner(self):
        if len(self._player_distances) < 2:
            return (False, None, None)

        player_sids = list(self._player_distances.keys())
        p1_distance = self._player_distances[player_sids[0]]
        p2_distance = self._player_distances[player_sids[1]]

        distance_diff = abs(p1_distance - p2_distance)

        if distance_diff >= self._win_distance:
            winner_sid = player_sids[0] if p1_distance > p2_distance else player_sids[1]
            print("winner by distance:", winner_sid)
            return (True, winner_sid, "distance")

        if self._game_started and time.time() - self._start_time >= self._game_duration:
            winner_sid = player_sids[0] if p1_distance > p2_distance else player_sids[1]
            return (True, winner_sid, "time")

        return (False, None, None)


    def start_game(self):
        self._game_started = True
        self._start_time = time.time()


    # --- GETTERS ---
    def get_max_players(self):
        return self._max_players

    def get_players_values(self):
        return list(self._players.values())

    def get_players(self):
        return self._players

    def get_game_started(self):
        return self._game_started

    def get_chunk_cache(self):
        return self._chunk_cache

    def get_room_code(self):
        return self._room_code

    def get_random_seed(self):
        return self._random_seed

    def get_start_time(self):
        return self._start_time

    def end_time(self):
        return time.time()

    def get_winner(self):
        return self._winner


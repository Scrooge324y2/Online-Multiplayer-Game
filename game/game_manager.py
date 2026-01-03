from game.logic import ProceduralGenerator
from database import Game, UserGame
import random
from datetime import datetime
import time

class GameManager:
    def __init__(self, code):
        self._max_players = 2
        self._players = {}
        self._chunk_cache = {}
        self._room_code = code
        self._random_seed = random.randint(1, 10000)
        self._start_time = 0
        self._winner = None
        self._win_distance = 5000
        self._player_distances = {}
        self._is_over = False
        self._generator = ProceduralGenerator(seed=self._random_seed)
        self._started = False
        self._ready_sids = set()#





    def add_player(self, user_id, sid, username):
        if user_id in self._players:
            print(f"User {user_id} already in game")
            self._players[user_id]['sid'] = sid
            return False

        if len(self._players) >= self._max_players:
            return False
        self._players[user_id] = {'sid': sid, 'username':username, 'x': 100, 'y': 450}
        return True

    def remove_player(self, sid):
        for user_id, player in list(self._players.items()):
            if player['sid'] == sid:
                del self._players[user_id]
                break

        if len(self._players) < self._max_players:
            self._started = False

    def all_players_ready(self):
        return len(self._players) == self._max_players

    def update_position(self, sid, x, y):
        for player in self._players.values():
            if player['sid'] == sid:
                player['x'] = x
                player['y'] = y
                return player
        return None

    def get_chunk(self, offset):
        print(f"chunk cache keys: {list(self._chunk_cache.keys())}")
        if offset in self._chunk_cache:
            return self._chunk_cache[offset]

        chunk = self._generator.generate_valid_chunk(offset=offset)
        if chunk is None:
            print("ERROR: generator returned None, using flat chunk")
            chunk = self._generator.generate_flat_chunk(offset=offset)
        self._chunk_cache[offset] = chunk
        return chunk


    def update_sid(self, user_id, new_sid):#updates a player's socket ID wghen they reconnect
        if user_id in self._players:
            self._players[user_id]['sid'] = new_sid
            return True
        else:
            return False

    def update_distance(self, sid, new_x):
        for user_id, player in self._players.items():
            if player['sid'] == sid:
                old_x = player.get('furthest_x', 100)
                if new_x > old_x:
                    self._player_distances[user_id] = new_x
                    player['furthest_x'] = new_x
                return

    def get_distance_between_players(self):
        if len(self._player_distances) < 2:
            return 0

        player_sids = list(self._player_distances.keys())
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

        players = list(self._player_distances.items())
        (u1, d1), (u2, d2) = players

        if abs(d1 - d2) >= self._win_distance:
            winner_user_id = u1 if d1 > d2 else u2
            return (True, winner_user_id, "distance")

        return (False, None, None)


    def start_game(self):
        self._started = True
        self._start_time = datetime.now()

    def end_game(self, winner_user_id):
        print("Ending game...")
        if not self._is_over:
            game_id = Game.add_game(
                winnerID=winner_user_id,
                start_time=self._start_time,
                end_time=datetime.now(),
                random_seed=self._random_seed,
            )
            for user_id in self._players.keys():
                UserGame.add_user_game(user_id, game_id)
            self._is_over = True



    def get_max_players(self):
        return self._max_players

    def get_players_values(self):
        return list(self._players.values())

    def get_players(self):
        return self._players

    def is_over(self):
        return self._is_over

    def get_sid(self, user_id):
        if user_id in self._players:
            return self._players[user_id]['sid']
        return None

    def mark_ready(self, user_id):
        self._ready_sids.add(user_id)

    def all_ready(self):
        return len(self._ready_sids) == 2

    def can_start(self):
        return self.all_ready() and not self._started





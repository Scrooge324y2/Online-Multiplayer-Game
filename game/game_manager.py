from game.logic import ProceduralGenerator
from database import Game, UserGame
import random
from datetime import datetime
from game.player import Player
class GameManager:
    def __init__(self, code):
        self._max_players = 2
        self._players = {}
        self._chunk_cache = {}
        self._room_code = code
        self._random_seed = random.randint(1, 10000)
        self._start_time = 0
        self._win_distance = 1500
        self._is_over = False
        self._generator = ProceduralGenerator(seed=self._random_seed)
        self._started = False
        self._ready_sids = set()
        self._difficulty_increase_per_chunk = 5





    def add_player(self, user_id, sid, username):
        if user_id in self._players:
            print(f"User {user_id} already in game")
            self._players[user_id].sid = sid
            return False

        if len(self._players) >= self._max_players:
            return False
        self._players[user_id] = Player(user_id, sid, username)
        return True

    def all_players_ready(self):
        return len(self._players) == self._max_players

    def update_position(self, sid, x, y):
        for player in self._players.values():
            if player.sid == sid:
                player.update_position(x, y)
                player.update_distance(x)
                return player
        return None

    def get_chunk(self, offset):
        if offset in self._chunk_cache:
            return self._chunk_cache[offset]

        chunk, biome_name = self._generator.generate_valid_chunk(offset=offset, prev_chunk=self._chunk_cache.get(offset - 1, (None, None))[0])

        if chunk is None:
            chunk = self._generator.generate_flat_chunk(offset=offset)
            biome_name = "Plain"

        self._chunk_cache[offset] = chunk, biome_name
        self._generator.increase_difficulty(self._difficulty_increase_per_chunk)
        return chunk, biome_name


    def update_sid(self, user_id, new_sid):#updates a player's socket ID when they reconnect
        if user_id in self._players:
            self._players[user_id].update_sid(new_sid)
            return True
        return False


    def check_winner(self):
        players = list(self._players.values())
        p1, p2 = players

        if abs(p1.distance_travelled - p2.distance_travelled) >= self._win_distance:
            winner = p1 if p1.distance_travelled > p2.distance_travelled else p2
            return True, winner.user_id, "distance"

        return (False, None, None)


    def start_game(self):
        self._started = True
        self._start_time = datetime.now()

    def end_game(self, winner_user_id, reason):
        if reason == "opponent_left":
            self._is_over = True
            return

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


    def get_players_values(self):
        return [player.to_dict() for player in self._players.values()]

    def is_over(self):
        return self._is_over

    def mark_ready(self, user_id):
        self._ready_sids.add(user_id)

    def all_ready(self):
        return len(self._ready_sids) == 2

    def can_start(self):
        return self.all_ready() and not self._started

    def get_opponent_user_id(self, user_id):
        for other_user_id in self._players:
            if other_user_id != user_id:
                return other_user_id
        return None

    def get_opponent_username(self, user_id):
        opponent_id = self.get_opponent_user_id(user_id)
        if opponent_id is None:
            return None
        return self._players[opponent_id].username

    def has_started(self):
        return self._started

    def get_player_username(self, user_id):
        if user_id in self._players:
            return self._players[user_id].username
        return None

    def get_relative_distance(self, requesting_user_id):
        players = list(self._players.values())

        if len(players) < 2:
            return 0

        p1, p2 = players

        if p1.user_id == requesting_user_id:
            user, opponent = p1, p2
        else:
            user, opponent = p2, p1

        return user.distance_travelled - opponent.distance_travelled









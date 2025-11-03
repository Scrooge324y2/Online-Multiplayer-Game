from game.logic import generate_chunk

class GameManager:
    def __init__(self):
        self.max_players = 2
        self.players = {}
        self.game_started = False
        self.chunk_cache = []

    def add_player(self, sid):
        if len(self.players) >= self.max_players:
            return False
        self.players[sid] = {'id': sid, 'x': 100, 'y': 450}

    def remove_player(self, sid):
        if sid in self.players:
            del self.players[sid]
        if len(self.players) < self.max_players:
            self.game_started = False

    def all_players_ready(self):
        return len(self.players) == self.max_players


    def get_players(self):
        print(list(self.players.values()))
        return list(self.players.values()) #creates a list of the values in the players dict

    def update_position(self, sid, x, y):
        if sid in self.players:
            self.players[sid]['x'] = x
            self.players[sid]['y'] = y
            return self.players[sid]
        return None

    def get_chunk(self, offset):
        if offset < len(self.chunk_cache):
            return self.chunk_cache[offset]
        else:
            chunk = generate_chunk(offset=offset)
            self.chunk_cache.append(chunk)
            return chunk

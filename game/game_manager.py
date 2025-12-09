from game.logic import generate_chunk

class GameManager:
    def __init__(self, code):
        self.max_players = 2
        self.players = {}
        self.game_started = False
        self.chunk_cache = []
        self.room_code = code

    def add_player(self, sid):
        if len(self.players) >= self.max_players:
            return False
        self.players[sid] = {'id': sid, 'x': 100, 'y': 450}
        return True

    def remove_player(self, sid):
        if sid in self.players:
            del self.players[sid]
        if len(self.players) < self.max_players:
            self.game_started = False

    def all_players_ready(self):
        return len(self.players) == self.max_players

    def get_players(self):
        print(list(self.players.values()))
        return list(self.players.values())

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

    def update_sid(self, old_sid, new_sid):#updates a player's socket ID wghen they reconnect
        if old_sid in self.players:
            # Get the player data
            player_data = self.players.pop(old_sid)
            # Update the ID field
            player_data['id'] = new_sid
            # Store with new socket ID as key
            self.players[new_sid] = player_data
            print(f"  Successfully updated player: {old_sid} → {new_sid}")
            return True
        else:
            print(f"  Warning: old_sid {old_sid} not found in players")
            print(f"  Current players: {list(self.players.keys())}")
            return False
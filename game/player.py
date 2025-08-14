from entity import Entity
class Player(Entity):
    def __init__(self, x, y, width, height, colour):
        super().__init__(x, y, width, height, True, colour)
        self.score = 0

    def move(self, dx, dy, game_map):
        super().move(dx, dy, game_map)

    def get_state(self):
        state = super().get_state()
        state['score'] = self.score
        return state
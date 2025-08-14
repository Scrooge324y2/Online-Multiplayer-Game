class Entity:
    def __init__(self, x, y, width, height, alive, colour):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.alive = True
        self.colour = colour

    def move(self, dx, dy, game_map):
        newX = self.x + dx
        newY = self.y + dy

        if not (0 <= newX < len(game_map) and 0 <= newY < len(game_map[0])):
            return

        if game_map[newX][newY] != 1: #prevents it from moving through ground and platforms
            self.x = newX
            self.y = newY

    def get_state(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'alive': self.alive,
            'colour': self.colour
        }



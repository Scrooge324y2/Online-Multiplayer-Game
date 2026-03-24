class Player:
    def __init__(self, user_id, sid, username):
        self.user_id = user_id
        self.sid = sid
        self.username = username
        self.x = 100
        self.y = 450
        self.distance_travelled = self.x

    def update_position(self, x, y):
        self.x = x
        self.y = y

    def update_sid(self, new_sid):
        self.sid = new_sid

    def update_distance(self, new_x):
        if new_x > self.distance_travelled:
            self.distance_travelled = new_x

    def to_dict(self):
        return {
            'sid': self.sid,
            'user_id': self.user_id,
            'username': self.username,
            'x': self.x,
            'y': self.y
        }



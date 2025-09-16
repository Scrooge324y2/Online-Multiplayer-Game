from flask_socketio import emit
from game.logic import generate_chunk


def register_socket_events(socketio):
    @socketio.on('connect')
    def on_connect():
        print('Client connected')
        chunk = generate_chunk()
        emit('map', {'map': chunk})

    @socketio.on('requestChunk')
    def send_chunk(offset):
        print(offset)
        chunk = generate_chunk(offset=int(offset))
        print('sending chunk')
        emit('map', {'map': chunk})
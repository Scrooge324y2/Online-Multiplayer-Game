from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from game.logic import generate_chunk

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

@app.route('/')
def game():
    return render_template('game.html')

@app.route('/login')


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


if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, port=5000)



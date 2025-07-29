from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from game.logic import generate_map

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='+')

@app.route('/')
def game():
    return render_template('game.html')

@socketio.on('connect')
def on_connect():
    print('Client connected')
    game_map = generate_map()
    emit('map', {'map': game_map})

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

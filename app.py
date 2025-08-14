from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from game.logic import generate_map

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

@app.route('/')
def game():
    return render_template('game.html')


@socketio.on('connect')
def on_connect():
    print('Client connected')
    game_map = generate_map()
    emit('map', {'map': game_map})

if __name__ == '__main__':
    #import eventlet
    #import eventlet.wsgi
    #eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, port=5000)
    #socketio.run(app, host="127.0.0.1", port=5000)


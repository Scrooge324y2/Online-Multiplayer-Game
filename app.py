from flask import Flask, render_template
from flask_socketio import SocketIO



app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')


from game.sockets import register_socket_events
register_socket_events(socketio)
@app.route('/')
def game():
    return render_template('game.html')

@app.route('/login')
def login():
    return render_template("login.html")



if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, port=5000)



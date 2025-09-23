from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
from database import Database

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')



users={}
from game.sockets import register_socket_events
register_socket_events(socketio)
@app.route('/')
def game():
    return render_template('game.html')

@app.route('/login')
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and password in users[username]:
            session['username'] = username
            return redirect(url_for('game'))
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users[username] = password
        return redirect(url_for('login'))
    return render_template("register.html")





if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, port=5000)



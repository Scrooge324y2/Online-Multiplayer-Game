from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
from database import User
import random
import string
from game.game_manager import GameManager

app = Flask(__name__)
app.secret_key = 'sadfsad'
socketio = SocketIO(app, cors_allowed_origins='*', manage_session=True)

games = {}
from game.sockets import register_socket_events
register_socket_events(socketio, games)

#@app.route('/')
@app.route('/game')
def game():
    #if 'username' not in session:
        #return redirect(url_for('login'))
    if "game_code" not in session:
        return redirect(url_for("play"))
    return render_template('game.html')

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.authenticate_user(username, password):
            session['username'] = username #creates session for the user
            return redirect(url_for('menu'))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(username, password)
        if not User.validate_username(username):
            return render_template("register.html", error="Username already in use")
        User.add_user(username, password)
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/menu")
def menu():
    #if "username" not in session:
        #return redirect(url_for("login"))
    return render_template("menu.html")

@app.route("/leaderboard")
def leaderboard():
    return "<h1>Leaderboard</h1>"

@app.route("/settings")
def settings():
    return "<h1>Settings</h1>"

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

#@app.route("/")
@app.route("/play")
def play():
    #if "username" not in session:
        #return redirect(url_for("login"))
    return render_template("play.html")

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4)) #Generates a random code of 4 uppercase letters


@app.route("/create_game")
def create_game():
    code = generate_code()
    new_game = GameManager()
    games[code] = new_game
    print(f"games: {games}")
    session["game_code"] = code
    return redirect(url_for("waiting_room"), code=code)

@app.route("/join_game", methods=["POST"])
def join_game():
    code = request.form["game_code"].strip().upper()
    session['game_code'] = code
    return redirect(url_for("waiting_room"), code=code)


@app.route("/waiting_room")
def waiting_room():
    if "game_code" not in session:
        return redirect(url_for("play"))
    return render_template("waiting_room.html", code=session["game_code"])

@app.route("/matchmaking")
def matchmaking():
    return "<h1>matchmaking page</h1>"



if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)



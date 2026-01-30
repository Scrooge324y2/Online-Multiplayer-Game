from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO
from database import User
import random
import string
from game.game_manager import GameManager
from game.matchmaking import MatchmakingQueue
import socket


app = Flask(__name__)
app.secret_key = 'sadfsad'

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    manage_session=False,
    cookie='io',
)

games = {}
from game.sockets import register_socket_events
register_socket_events(socketio, games, MatchmakingQueue())


#@app.route('/')
@app.route('/game')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))

    code = request.args.get('code') or session.get('game_code')

    if not code:
        return redirect(url_for("play"))

    # Always update session with code from URL if provided
    if request.args.get('code'):
        session['game_code'] = code
        session.modified = True

    return render_template('game.html')

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.authenticate_user(username, password):
            session['username'] = username #creates session for the user
            session['user_id'] = User.get_user_id(username) #used when sending game details to database
            session.modified = True
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
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("menu.html", username=session.get("username"))

@app.route("/leaderboard")
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    top_players = User.get_top_10_by_wins()
    return render_template("leaderboard.html", players=top_players)



@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

#@app.route("/")
@app.route("/play")
def play():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("play.html")

def generate_code():
    code = ''.join(random.choices(string.ascii_uppercase, k=4)) #Generates a random code of 4 uppercase letters
    if code in games:
        return generate_code()
    return code


@app.route("/create_game")
def create_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    code = generate_code()
    new_game = GameManager(code)
    games[code] = new_game
    print(f"games: {games}")
    session["game_code"] = code
    return redirect(url_for("waiting_room", code=code))

@app.route("/join_game", methods=["POST"])
def join_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    code = request.form["game_code"].strip().upper()
    session['game_code'] = code
    return redirect(url_for("waiting_room", code=code))


@app.route("/waiting_room")
def waiting_room():
    if 'username' not in session:
        return redirect(url_for('login'))
    if "game_code" not in session:
        return redirect(url_for("play"))
    return render_template("waiting_room.html", code=session["game_code"])

@app.route("/matchmaking")
def matchmaking():
    if 'username' not in session:
        return redirect(url_for('login'))
    session['in_matchmaking'] = True
    return render_template("matchmaking.html")

@app.route("/game_over")
def game_over():
    if 'username' not in session:
        return redirect(url_for('login'))
    if "game_code" not in session:
        return redirect(url_for("play"))
    return render_template("game_over.html")

@app.route("/profile")
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    user_id = session.get("user_id")
    username = session.get("username")
    game_history = User.get_game_history(user_id)
    win_rate = User.get_win_rate(user_id)
    total_games = len(game_history)
    return render_template("profile.html", username=username, game_history=game_history, win_rate=win_rate, total_games=total_games)



def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "localhost"
    finally:
        s.close()
    return ip

if __name__ == '__main__':
    ip = get_local_ip()
    print(f"Server running on:")
    print(f"  Local:   http://localhost:5000")
    print(f"  Network: http://{ip}:5000")

    socketio.run(app, host="0.0.0.0", port=5000)





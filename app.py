from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO
from database import User
import random
import string
from game.game_manager import GameManager
from game.matchmaking import MatchmakingQueue
import socket
from functools import wraps


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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


#@app.route('/')
@app.route('/game')
@login_required
def game():
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash("Username and password cannot be empty", "error")
            return redirect(url_for('login'))

        if User.authenticate_user(username, password):
            user_id = User.get_user_id(username)
            if not user_id:
                flash("Login error. Please try again.", "error")
                return redirect(url_for('login'))

            session['username'] = username #creates session for the user
            session['user_id'] = User.get_user_id(username) #used when sending game details to database
            session.modified = True
            return redirect(url_for('menu'))
        else:
            flash("Incorrect username or password", "error")
            return redirect(url_for('login'))
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash("Username and password cannot be empty", "error")
            return redirect(url_for('register'))

        if not User.validate_username(username):
            flash("Username is already in use", "error")
            return redirect(url_for('register'))

        if not User.add_user(username, password):
            flash("Registration failed. Please try again.", "error")
            return redirect(url_for('register'))

        user_id = User.get_user_id(username)
        if not user_id:
            flash("Registration succeeded but error retrieving user. Please login.", "error")
            return redirect(url_for('login'))

        session['username'] = username
        session['user_id'] = user_id
        session.modified = True

        key = User.create_recovery_key(session['user_id'])#
        if key:
            session['recovery_key'] = key
            return redirect(url_for('show_recovery_key'))
        else:
                flash("Registration succeeded but error creating recovery key. Please create one in your profile.", "error")
                return redirect(url_for('menu'))

    return render_template("register.html")

@app.route("/menu")
@login_required
def menu():
    return render_template("menu.html", username=session.get("username"))

@app.route("/leaderboard")
@login_required
def leaderboard():
    top_players = User.get_top_10_by_wins()
    if top_players is None:
        flash("Error loading leaderboard", "error")
        top_players = []

    return render_template("leaderboard.html", players=top_players)



@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

#@app.route("/")
@app.route("/play")
@login_required
def play():
    return render_template("play.html")

def generate_code():
    code = ''.join(random.choices(string.ascii_uppercase, k=4)) #Generates a random code of 4 uppercase letters
    if code in games:
        return generate_code()
    return code


@app.route("/create_game")
@login_required
def create_game():
    code = generate_code()
    new_game = GameManager(code)
    games[code] = new_game
    print(f"games: {games}")
    session["game_code"] = code
    return redirect(url_for("waiting_room", code=code))

@app.route("/join_game", methods=["POST"])
@login_required
def join_game():
    code = request.form.get("game_code", "").strip().upper()

    if not code:
        flash("Game code cannot be empty.", "error")
        return redirect(url_for("play"))

    if code in games:
        session['game_code'] = code
        session.modified = True
        return redirect(url_for("waiting_room", code=code))
    else:
        flash("Invalid game code.", "error")
        return redirect(url_for("play"))


@app.route("/waiting_room")
@login_required
def waiting_room():
    if "game_code" not in session:
        return redirect(url_for("play"))
    return render_template("waiting_room.html", code=session["game_code"])

@app.route("/matchmaking")
@login_required
def matchmaking():
    session['in_matchmaking'] = True
    return render_template("matchmaking.html")

@app.route("/game_over")
@login_required
def game_over():
    if "game_code" not in session:
        return redirect(url_for("play"))
    return render_template("game_over.html")

@app.route("/profile")
@login_required
def profile():
    username = session.get("username")
    return render_template("profile.html", username=username)

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "")
        recovery_key = request.form.get("recovery_key", "")

        if not username or not new_password or not recovery_key:
            flash("All fields are required.", "error")
            return redirect(url_for("forgot_password"))

        user_id = User.get_user_id(username)
        if user_id is None:
            flash("Username not found.", "error")
            return redirect(url_for("forgot_password"))

        if not User.authenticate_recovery_key(user_id, recovery_key):
            flash("Incorrect recovery key", "error")
            return redirect(url_for("forgot_password"))

        if not User.change_password(user_id, new_password):
            flash("Error resetting password. Please try again.", "error")
            return redirect(url_for("forgot_password"))

        flash("Password reset successful.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

@app.route("/delete_account", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "POST":
        password = request.form.get("password", "")
        username = session.get("username")
        user_id = session.get("user_id")

        if not password:
            flash("Password is required to delete account.", "error")
            return redirect(url_for("delete_account"))

        if not User.authenticate_user(username, password):
            flash("Password is incorrect.", "error")
            return redirect(url_for("delete_account"))

        if not User.deactivate_user(user_id):
            flash("Error deleting account. Please try again.", "error")
            return redirect(url_for("delete_account"))

        session.pop("username", None)
        session.pop("user_id", None)
        session.modified = True
        flash("Account deleted successfully.", "success")
        return redirect(url_for("register"))

    return render_template("delete_account.html")

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        username = session.get("username")
        user_id = session.get("user_id")

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "error")
            return redirect(url_for("change_password"))

        if not User.authenticate_user(username, current_password):
            flash("Current password is incorrect.", "error")
            return redirect(url_for("change_password"))

        if not User.change_password(user_id, new_password):
            flash("Error changing password. Please try again.", "error")
            return redirect(url_for("change_password"))

        flash("Password changed successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("change_password.html")


@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():
    if request.method == "POST":
        new_username = request.form.get("new_username", "").strip()
        user_id = session.get("user_id")

        if not new_username:
            flash("New username cannot be empty.", "error")
            return redirect(url_for("change_username"))

        if not User.validate_username(new_username):
            flash("Username already in use.", "error")
            return redirect(url_for("change_username"))

        if not User.change_username(user_id, new_username):
            flash("Error changing username. Please try again.", "error")
            return redirect(url_for("change_username"))

        session['username'] = new_username
        session.modified = True
        flash("Username changed successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("change_username.html")

@app.route("/recovery_key")
@login_required
def show_recovery_key():
    key = session.pop("recovery_key", None) # Retrieve and remove the recovery key from session
    if key is None:
        return redirect(url_for("menu"))

    return render_template("recovery_key.html", recovery_key=key)

@app.route("/new_recovery_key", methods=["GET", "POST"])
@login_required
def new_recovery_key():
    if request.method == "POST":
        password = request.form.get("password", "")
        username = session.get("username")
        user_id = session.get("user_id")

        if not password:
            flash("Password is required.", "error")
            return redirect(url_for("new_recovery_key"))

        if not User.authenticate_user(username, password):
            flash("Password is incorrect.", "error")
            return redirect(url_for("new_recovery_key"))

        key = User.create_recovery_key(user_id, new_key=True)
        if not key:
            flash("Error creating new recovery key. Please try again.", "error")
            return redirect(url_for("new_recovery_key"))

        session["recovery_key"] = key
        session.modified = True
        return redirect(url_for("show_recovery_key"))

    return render_template("new_recovery_key.html")

@app.route("/game_history")
@login_required
def game_history():
    user_id = session.get("user_id")
    username = session.get("username")

    game_history = User.get_game_history(user_id)
    if game_history is None:
        flash("Error loading game history", "error")
        game_history = []

    win_rate = User.get_win_rate(user_id)
    if win_rate is None:
        win_rate = 0.0

    total_games = len(game_history)

    return render_template("game_history.html", username=username, game_history=game_history, win_rate=win_rate, total_games=total_games)



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





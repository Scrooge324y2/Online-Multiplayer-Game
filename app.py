from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
from database import Users

app = Flask(__name__)
app.secret_key = 'sadfsad'
socketio = SocketIO(app, cors_allowed_origins='*')



users={}
from game.sockets import register_socket_events
register_socket_events(socketio)

@app.route('/')
def game():
    #if 'username' not in session:
        #return redirect(url_for('login'))
    return render_template('game.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if Users.authenticate_user(username, password):
            session['username'] = username #creates session for the user
            return redirect(url_for('game'))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(username, password)
        if not Users.validate_username(username):
            return render_template("register.html", error="Username already in use")
        Users.add_user(username, password)
        return redirect(url_for('login'))
    return render_template("register.html")





if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, port=5000)



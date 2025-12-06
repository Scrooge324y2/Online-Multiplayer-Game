import code

from flask import request, session
from flask_socketio import emit, join_room

from game.game_manager import GameManager
from game.logic import generate_chunk



def register_socket_events(socketio, games):
    print(f"sockets, games: {games}")

    @socketio.on('connect')
    def on_connect():
        print(f'Client connected: {request.sid}')



    @socketio.on('joinGame')
    def join_game(data):
        code = data['code']

        if code not in games:
           games[code] = GameManager()

        session['game_code'] = code

        game = games[code]
        game.add_player(request.sid)

        print(len(game.players))
        join_room(code)
        print(f'game code: {game.room_code}, players: {game.players}')

        if game.all_players_ready():
            print("all players ready")
            players = socketio.server.manager.rooms["/"].get(code, set())
            print(f'game code: {game.room_code}, players: {game.players}')
            socketio.emit("startGame", {'players':game.get_players()}, room=code)

    @socketio.on('rejoinRoom')
    def rejoin_room():
        code = session.get("game_code")
        if code:
            join_room(code)
            print(request.sid, "rejoined room", code)




    @socketio.on('requestChunk')
    def on_request_chunk(offset):
        code = session.get('game_code')
        if not code or code not in games:
            return
        chunk = games[code].get_chunk(offset=int(offset))
        emit('map', {'map': chunk})


    @socketio.on('playerMovement')
    def on_player_movement(data):
        sid = request.sid
        code = session.get('game_code')

        if not code or code not in games:
            return

        game = games[code]
        updatedPos = game.update_position(sid, data.get('x',0), data.get('y',0)) #gets the current position of the player from the frontend
        #print(f"current state: {game.players}")
        if updatedPos:
            socketio.emit('playerMoved', updatedPos, room=code)

    @socketio.on('disconnect')
    def on_disconnect():
        code = session.get('game_code')
        if not code or code not in games:
            return
        game = games[code]
        sid = request.sid
        print(f'Client disconnected: {sid}')
        game.remove_player(sid)
        socketio.emit('playerDisconnected', {'id': sid}, room=code)


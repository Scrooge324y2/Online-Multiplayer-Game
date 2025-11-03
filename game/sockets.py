from flask import request
from flask_socketio import emit

from game.game_manager import GameManager
from game.logic import generate_chunk



def register_socket_events(socketio):
    game = GameManager()

    @socketio.on('connect')
    def on_connect():
        sid = request.sid
        #game.add_player(sid)
        print(f'Client connected: {sid}')

        if not game.add_player(sid):
            emit('gameFull')
            return

        chunk = game.get_chunk(0)
        emit('map', {'map': chunk})

        if game.all_players_ready():# and not game.game_started:
            game.game_started = True
            print('players: ' , game.get_players())
            socketio.emit('startGame', {'players': game.get_players()})

    @socketio.on('requestChunk')
    def on_request_chunk(offset):
        chunk = game.get_chunk(offset=int(offset))
        emit('map', {'map': chunk})


    @socketio.on('playerMovement')
    def on_player_movement(data):
        sid = request.sid
        updated = game.update_position(sid, data.get('x',0), data.get('y',0))
        if updated:
            for pid in game.players:
                if pid != sid:
                    socketio.emit('playerMoved', updated, to=pid) #send only to the socket whose ID equal pid

    @socketio.on('disconnect')
    def on_disconnect():
        sid = request.sid
        print(f'Client disconnected: {sid}')
        game.remove_player(sid)
        socketio.emit('playerDisconnected', {'id': sid})


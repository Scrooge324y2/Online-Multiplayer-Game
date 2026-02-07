from flask import request, session
from flask_socketio import emit, join_room, rooms
from game.game_manager import GameManager


def register_socket_events(socketio, games, matchmaking_queue):
    print(f"sockets, games: {games}")

    @socketio.on('connect')
    def on_connect():
        print(f'Client connected: {request.sid}')
        print(f'Session game_code: {session.get("game_code")}')
        print(f'Current rooms: {rooms()}')


    @socketio.on('joinMatchmaking')
    def join_matchmaking(data):
        sid = request.sid
        username = session.get("username")

        matchmaking_queue.add_player(sid, username)
        print(f"Player {sid} ({username}) joined matchmaking queue.")

        match = matchmaking_queue.find_match()
        if match:
            player1, player2 = match
            code = matchmaking_queue.generate_game_code()
            game = GameManager(code) #create new game
            games[code] = game

            socketio.emit('matchFound', {
                'code': code,
                'opponent': player2['username']
            }, room=player1['sid'])

            socketio.emit('matchFound', {
                'code': code,
                'opponent': player1['username']
            }, room=player2['sid'])


    @socketio.on('leaveMatchmaking')
    def leave_matchmaking():
        sid = request.sid
        matchmaking_queue.remove_player(sid)
        print(f'Player {sid} left matchmaking')
        emit('queueLeft', {'message': 'Left matchmaking'})



    @socketio.on('joinGame')
    def join_game(data):
        code = data['code']

        if code not in games:
            print("CODE NOT FOUND, CREATING NEW GAME")
            games[code] = GameManager(code)

        session['game_code'] = code #stores to update later
        session.modified = True  # Force session to save

        game = games[code]
        join_room(code)
        game.add_player(user_id=session['user_id'], sid=request.sid, username=session['username'])
        if game.all_players_ready():
            socketio.emit("gameReady")


    @socketio.on('rejoinRoom')
    def rejoin_room():
        print("REJOINING ROOM")
        code = session.get("game_code")
        if code not in games:
            print("REDIRECTING TO PLAY")
            emit("redirect_to_play") #redirect player to lobby if they are not part of a game (happens when reloading)
            return
        game = games[code]

        game.update_sid(session['user_id'], request.sid)
        join_room(code)

        game.mark_ready(session['user_id'])

        # Start the game if safe
        if game.can_start():
            print("STARTING GAME")
            game.start_game()
            socketio.emit("startGame",{"players": game.get_players_values()},room=code)


    @socketio.on('requestChunk')
    def on_request_chunk(offset):
        #print(f"chunk requested, offset: {offset}")
        code = session.get('game_code')
        if not code or code not in games:
            print(f"ERROR: requestChunk - code={code}, exists={code in games if code else False}")
            return
        chunk = games[code].get_chunk(offset=int(offset))
        emit('map', {'map': chunk})
        #print(f"chunk sent, offset: {offset}")



    @socketio.on('playerMovement')
    def on_player_movement(data):
        print("PLAYER MOVEMENT")
        sid = request.sid
        code = session.get('game_code')

        if not code or code not in games:
            print(f"ERROR: playerMovement - code={code}, exists={code in games if code else False}")
            return

        game = games[code]
        if game.is_over(): #stops the function from running if the game has ended
            print("PLAYER MOVEMENT IGNORED - GAME OVER")
            return

        # Update this player's position in the game
        updatedPos = game.update_position(sid, data.get('x', 0), data.get('y', 0))
        print("UPDATED POS: ", updatedPos)

        if updatedPos:
            socketio.emit('playerMoved', updatedPos, room=code,include_self=False)  # sends position only to other player
            game.update_distance(sid, data.get('x', 0))
            has_winner, winner_user_id, reason = game.check_winner()

            if has_winner:
                print(f"Game over! Winner: {winner_user_id} Reason: {reason}")
                if session['user_id'] == winner_user_id:
                    winner_username = session.get("username")
                    game.end_game(session.get("user_id"), reason=None)
                    socketio.emit('gameOver', {'winnerUsername': winner_username,'reason': reason}, room=code)
                    del games[code]
                    session.pop('game_code', None)
                    session.modified = True



    @socketio.on('disconnect')
    def on_disconnect():
        sid = request.sid


        if matchmaking_queue.is_player_in_queue(sid):
            matchmaking_queue.remove_player(sid)


        code = session.get('game_code')

        print(f'\n=== DISCONNECT ===')
        print(f"username: {session.get('username')}")
        print(f'Client disconnected: {sid}')
        print(f'Game code: {code}')

        # Handle active game
        if not code or code not in games:
            return

        game = games[code]

        if game.is_over():
            return

        opponent_id = game.get_opponent_user_id(session['user_id'])
        opponent_username = game.get_opponent_username(session['user_id'])

        if opponent_id and game.has_started():
            game.end_game(opponent_id, reason='opponent_left')
            socketio.emit('gameOver',{'winnerUsername': opponent_username, 'reason': 'opponent_left'},room=code)
            del games[code]










from flask import request, session
from flask_socketio import emit, join_room, rooms
from game.game_manager import GameManager
from database import Game


def register_socket_events(socketio, games, matchmaking_queue):
    print(f"sockets, games: {games}")

    @socketio.on('connect')
    def on_connect():
        print(f'Client connected: {request.sid}')
        print(f'Session game_code: {session.get("game_code")}')
        print(f'Session old_sid: {session.get("old_sid")}')
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
            print("Creating GameManager for new code:", code)
            games[code] = GameManager(code)

        session['game_code'] = code
        # Store this socket ID so we can update it later when reconnecting
        session['old_sid'] = request.sid
        session.modified = True  # Force session to save

        print(f"\n=== JOIN GAME (WAITING ROOM) ===")
        print(f"Player {request.sid} joined room {code}")
        print(f"Saved to session: game_code={code}, old_sid={request.sid}")

        game = games[code]
        result = game.add_player(request.sid)

        join_room(code)

        print(f"Add player result: {result}")
        print(f"Total players in game: {len(game.get_players())}")
        print(f"Player list: {list(game.get_players().keys())}")
        print(f"Rooms for this socket: {rooms()}")
        print(f"================================\n")

        # Check if we have 2 players and start the game
        if game.all_players_ready():
            players_data = game.get_players_values()
            print(f"\n=== STARTING GAME ===")
            print(f"Emitting startGame to room {code}")
            print(f"Players data: {players_data}")
            print(f"====================\n")
            #socketio.emit("readyToStart", {'players': players_data}, room=code)
            socketio.emit("startGame", {'players': players_data}, room=code)
            game.start_game()

    @socketio.on('rejoinRoom')
    def rejoin_room():
        code = session.get("game_code")
        old_sid = session.get("old_sid")
        new_sid = request.sid

        print(f"\n========== REJOIN ROOM ==========")
        print(f"Old Socket ID from session: {old_sid}")
        print(f"New Socket ID (request.sid): {new_sid}")
        print(f"Game code from session: {code}")

        if not code:
            print(f"ERROR: No game code in session!")
            print(f"=================================\n")
            return

        if code not in games:
            print(f"ERROR: Game {code} not found in games dict!")
            print(f"Available games: {list(games.keys())}")
            print(f"=================================\n")
            return

        game = games[code]

        # Initialize tracking for this game if not exists
        if not hasattr(rejoin_room, 'game_data'): #checks if object has attribute
            rejoin_room.game_data = {}

        # Store original player list and track remappings
        if code not in rejoin_room.game_data:
            rejoin_room.game_data[code] = {
                'original_players': list(game.get_players().keys()),
                'remapped': {}  # {new_sid: old_sid}
            }
            print(f" Initialized tracking for {code}")
            print(f" Original players: {rejoin_room.game_data[code]['original_players']}")

        game_data = rejoin_room.game_data[code]
        original_players = game_data['original_players']

        print(f"Original players: {original_players}")
        print(f"Already remapped: {game_data['remapped']}")

        # Update the socket ID from old to new
        if old_sid and old_sid != new_sid:
            print(f"Has old_sid, calling game.update_sid({old_sid}, {new_sid})...")
            result = game.update_sid(old_sid, new_sid)
            game_data['remapped'][new_sid] = old_sid
            print(f"update_sid returned: {result}")
        else:
            print(f"No old_sid in session!")

            # Find which original player hasn't been remapped yet
            already_remapped_old = set(game_data['remapped'].values())
            print(f"Already remapped original players: {already_remapped_old}")

            # Find an original player that hasn't been remapped
            unmapped_originals = [p for p in original_players if p not in already_remapped_old]
            print(f"Unmapped original players: {unmapped_originals}")

            if unmapped_originals:
                # Check which unmapped original is still in current players
                for orig_player in unmapped_originals:
                    if orig_player in game.get_players():
                        print(f" Mapping {new_sid} to {orig_player}")
                        game.update_sid(orig_player, new_sid)
                        game_data['remapped'][new_sid] = orig_player
                        break
                else:
                    print(f"ERROR: No unmapped original player found in current game!")
            else:
                print(f"All original players remapped, adding as new...")
                result = game.add_player(new_sid)
                print(f"add_player returned: {result}")

        # Update session
        session['old_sid'] = new_sid
        session.modified = True

        #print(f"Players AFTER update: {list(game.get_players().keys())}")
        print(f"Remapping record: {game_data['remapped']}")

        # Join the socket.io room
        join_room(code)

        print(f" Socket {new_sid} joined room: {code}")
        print(f"=================================\n")

        # Send the current game state
        players_data = game.get_players_values()
        emit('startGame', {'players': players_data})

    @socketio.on('requestChunk')
    def on_request_chunk(offset):
        print("chunk requested")
        code = session.get('game_code')
        if not code or code not in games:
            print(f"ERROR: requestChunk - code={code}, exists={code in games if code else False}")
            return
        chunk = games[code].get_chunk(offset=int(offset))
        emit('map', {'map': chunk})

    @socketio.on('playerMovement')
    def on_player_movement(data):
        sid = request.sid
        code = session.get('game_code')

        if not code or code not in games:
            if not hasattr(on_player_movement, 'error_shown'):
                on_player_movement.error_shown = True
                print(f"ERROR: playerMovement - No game code or game not found")
            return

        game = games[code]

        # Initialize counter
        if not hasattr(on_player_movement, 'counter'): #debugging
            on_player_movement.counter = 0
        on_player_movement.counter += 1

        # Log first few movements for debugging
        if on_player_movement.counter <= 3:
            print(f"\n=== PLAYER MOVEMENT (#{on_player_movement.counter}) ===")
            print(f"Player {sid} sending position: ({data.get('x', 0):.1f}, {data.get('y', 0):.1f})")
            print(f"Game code: {code}")
            print(f"Players in game: {list(game.get_players().keys())}")
            print(f"Is player in game? {sid in game.get_players_values()}")

        # Update this player's position in the game
        updatedPos = game.update_position(sid, data.get('x', 0), data.get('y', 0))

        if on_player_movement.counter <= 3:
            print(f"update_position returned: {updatedPos}")

        if updatedPos:

            # Check what rooms this socket is in
            current_rooms = rooms()

            if on_player_movement.counter <= 3:
                print(f"  Broadcasting to room '{code}'")
                print(f"  Socket is in rooms: {current_rooms}")
                print(f"  Include self: False")
                print(f"=================================\n")

            # Broadcast to everyone in the room EXCEPT the sender
            socketio.emit('playerMoved', updatedPos, room=code, include_self=False)
        else:
            if on_player_movement.counter <= 3:
                print(f"  WARNING: update_position returned None!")
                print(f"  This means socket {sid} is not in game.get_players()")
                print(f"  Available players: {list(game.get_players().keys())}")
                print(f"=================================\n")

    @socketio.on('disconnect')
    def on_disconnect():
        sid = request.sid

        if matchmaking_queue.is_player_in_queue(sid):
            matchmaking_queue.remove_player(sid)
            print(f'Player {sid} removed from matchmaking queue on disconnect.')

        code = session.get('game_code')

        print(f'\n=== DISCONNECT ===')
        print(f'Client disconnected: {sid}')
        print(f'Game code: {code}')

        # Don't remove players on disconnect - they might be navigating to game page
        # We'll only remove them if they truly disconnect from the game page

        if code and code in games:
            game = games[code]
            #socketio.emit('playerDisconnected', {'id': sid}, room=code)


    @socketio.on('game_over')
    def on_game_over():
        Game.add_game(
            score=games['code'].get_score(),
            winnerID=games['code'].get_winner(),
            start_time=games['code'].get_start_time(),
            end_time=games['code'].get_end_time(),
            random_seed=games['code'].get_random_seed()
        )


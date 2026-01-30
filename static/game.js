let gameSocket = null;

const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    },
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 400 },
            debug: false
        }
    },
    scene: {
        preload: preload,
        create: create,
        update: update
    }
};
function tilesToPixels(tiles){
    return tiles * tileSize;
}
let game = new Phaser.Game(config);

let player;
let otherPlayer;
let platforms;
let cursors;
let chunkOffset = 0;
let chunkWidth = 20; //tiles per chunk
const tileSize = 40; //pixels per tile
const height = 600;
const MAX_JUMP_HEIGHT_TILES = 3;
const JUMP_VELOCITY = Math.sqrt(2 * 400 * (MAX_JUMP_HEIGHT_TILES * tileSize));
let mySocketId = null;
let sceneContext = null;
let lastSentX = null;
let lastSentY = null;
const SPEED_BOOST = 60;
const BACKWARDS_SPEED = 30;
const MAX_SPEED = 260;
const SPEED_INCREASE_PER_SECOND = 2.5;

function preload() {
}

function create() {
    function requestInitialChunkOnce() {
    if (sceneContext.initialChunkRequested) return;
    sceneContext.initialChunkRequested = true;
    chunkOffset = 0;
    gameSocket.emit('requestChunk', 0);
}
    sceneContext = this;

    // Create socket connection to server
    gameSocket = io();

    gameSocket.on("gameOver", (data) => {
        if (this.gameEnded) return;
        this.gameEnded = true;
        game.destroy(true)
        gameSocket.disconnect();
        history.replaceState(null, "", "/play");
        window.location.href = `/game_over?winner=${data.winnerUsername}&reason=${data.reason}`;
    });

    gameSocket.on("connect", () => {
        //console.log("Connected to server with ID:", gameSocket.id);
        mySocketId = gameSocket.id;
        gameSocket.emit("rejoinRoom");
        //console.log("calling rejoin room on connect");



    });

    gameSocket.on("reconnect", () => {
        //console.warn("Socket reconnected, rejoining room");
        gameSocket.emit("rejoinRoom");
    });

    platforms = this.physics.add.staticGroup();
    spikes = this.physics.add.staticGroup();
    this.spikes = spikes;
    this.chunksLoaded = false;
    this.offset = 0;
    this.requestingChunk = false;
    this.serverReady = false;
    //sceneContext.cameras.main.startFollow(player, true, 0.1, 0.1);

    // Handle map chunks
    gameSocket.on('map', (data) => {
        console.log("Received chunk:", chunkOffset);
        sceneContext.requestingChunk = false;
        chunkWidth = data.map[0].length;
        drawChunk(sceneContext, data.map, chunkOffset);
        chunkOffset++;
        sceneContext.chunksLoaded = true;

        const worldWidth = chunkOffset * chunkWidth * tileSize;
        sceneContext.physics.world.setBounds(0, 0, worldWidth, height);
        sceneContext.cameras.main.setBounds(0, 0, worldWidth, height);
        sceneContext.physics.world.colliders.update();
    });

    // Create user player (red square)
    player = this.add.rectangle(100, 450, tilesToPixels(1), tilesToPixels(1), 0xff0000);
    this.physics.add.existing(player);
    player.body.setCollideWorldBounds(true);
    this.playerCollider = this.physics.add.collider(player, platforms);
    player.body.allowSleep = false;
    player.baseSpeed = 100;      // constant baseline
    player.speed = player.baseSpeed;
    this.physics.add.overlap(player, spikes, onSpikeHit, null, this);




    cursors = this.input.keyboard.createCursorKeys();

    // Handle game start
    gameSocket.on('startGame', (data) => {
        sceneContext.serverReady = true;
        requestInitialChunkOnce();
        // Find my player data
        const myPlayer = data.players.find(p => p.id === mySocketId);
        const other = data.players.find(p => p.id !== mySocketId);

        if (myPlayer) {
            player.x = myPlayer.x;
            player.y = myPlayer.y;
        }

        // Create the other player (blue square)
        if (other) {
            if (otherPlayer) {
                otherPlayer.destroy();
            }

            otherPlayer = sceneContext.add.rectangle(other.x, other.y, tilesToPixels(1), tilesToPixels(1), 0x0000ff);
        }
    });

    gameSocket.on('syncState', (data) => {
        sceneContext.serverReady = true;
        requestInitialChunkOnce();
        const myPlayer = data.players.find(p => p.id === mySocketId);
        const other = data.players.find(p => p.id !== mySocketId);

        if (myPlayer) {
            player.x = myPlayer.x;
            player.y = myPlayer.y;
        }

        if (other && otherPlayer) {
            otherPlayer.x = other.x;
            otherPlayer.y = other.y;
        }
    });


    // Handle other player movement
    gameSocket.on("playerMoved", (data) => {
        if (data.id === mySocketId || !otherPlayer) return;
        otherPlayer.x = data.x;
        otherPlayer.y = data.y;

    });

    gameSocket.on('playerDisconnected', (data) => {
        if (otherPlayer && data.id !== mySocketId) {
            otherPlayer.destroy();
            otherPlayer = null;
        }
    });

    gameSocket.on('redirect_to_play', () => {
        sessionStorage.removeItem("loadedBefore");
        sessionStorage.setItem("flashMessage", "You were disconnected from the game.");
        window.location.replace("/play")
    });

    // Store socket reference
    this.gameSocket = gameSocket;


}




function update(time, delta) {
    if (!sceneContext.serverReady) return;
    if (!sceneContext.chunksLoaded) {
        player.body.setVelocityX(0);
        return;
}
    if (sceneContext.gameEnded) return;

    sceneContext.cameras.main.startFollow(player, true, 0.1, 0.1);

    if (!player) return;

    player.baseSpeed += SPEED_INCREASE_PER_SECOND * (delta / 1000); // Increase base speed over time
    player.baseSpeed = Math.min(player.baseSpeed, MAX_SPEED);


    const touchingGround = player.body.blocked.down;
    const touchingWall = player.body.blocked.left || player.body.blocked.right;
    const atBottomOfScreen = player.body.bottom >= sceneContext.cameras.main.worldView.bottom - 5;

    const jumpPressed = Phaser.Input.Keyboard.JustDown(cursors.up);

    let didWallJump = false;

    if (player.slowTimer > 0) {
        player.slowTimer -= delta / 1000;
        if (player.slowTimer <= 0) {
            player.speed = player.baseSpeed;
        }
    }



    // WALL JUMP
    if (jumpPressed && touchingWall && !player.body.blocked.up) {
        player.body.setVelocityY(-JUMP_VELOCITY * 0.85);

        const push = player.body.blocked.left ? 180 : -180;
        player.body.setVelocityX(push);
        didWallJump = true;
    }
    // NORMAL JUMP
    else if (jumpPressed && (touchingGround || atBottomOfScreen)) {
        player.body.setVelocityY(-JUMP_VELOCITY);
    }

    if (!didWallJump) {
        if (cursors.left.isDown) {
            player.body.setVelocityX(player.speed - (player.speed + BACKWARDS_SPEED));
        }
        else if (cursors.right.isDown) {
            player.body.setVelocityX(player.speed + SPEED_BOOST);
        }
        else {
            player.body.setVelocityX(player.speed);
        }
    }


    if (cursors.down.isDown && !touchingGround) {
        player.body.setVelocityY(200);
    }

    // Request new chunks
    if (player.x > (chunkOffset - 2) * chunkWidth * tileSize && !sceneContext.requestingChunk) {
        sceneContext.requestingChunk = true;
        gameSocket.emit('requestChunk', parseInt(chunkOffset));
    }

    // Send position to server
    if (gameSocket && gameSocket.connected && (player.x !== lastSentX || player.y !== lastSentY)) {
        gameSocket.emit('playerMovement', { x: player.x, y: player.y });
        lastSentX = player.x;
        lastSentY = player.y;


    }
}

function drawChunk(scene, chunk, offset) {
    for (let y = 0; y < chunk.length; y++) {
        for (let x = 0; x < chunk[y].length; x++) {
            if (chunk[y][x] === 1) {
                let plat = scene.add.rectangle(
                    (x + offset * chunk[y].length) * tileSize + tileSize / 2,
                    y * tileSize + tileSize / 2,
                    tileSize,
                    tileSize,
                    0x00ff00
                );
                scene.physics.add.existing(plat, true);
                platforms.add(plat);
            }else if (chunk[y][x] === 2) {
                const spike = createSpike(
                    scene,
                    (x + offset * chunk[y].length) * tileSize + tileSize / 2,
                    y * tileSize + tileSize/2
                );
                spikes.add(spike);
        }   }
    }
    platforms.children.each(p => p.body.updateFromGameObject());
    scene.physics.add.overlap(player, spikes, onSpikeHit, null, scene);


}


function createSpike(scene, x, y) {
    // Visual only
    scene.add.triangle(
        x, y,
        0, tileSize,
        tileSize, tileSize,
        tileSize / 2, 0,
        0xff0000
    );

    // Physics hitbox
    const hitbox = scene.add.zone(x, y, tileSize * 0.8, tileSize * 0.6);
    scene.physics.add.existing(hitbox, true);
    hitbox.body.updateFromGameObject();

    hitbox.isSpike = true;

    return hitbox;
}

function onSpikeHit(player, spike) {
    if (player.spikeCooldown) return;

    player.spikeCooldown = true;

    // Apply slowdown
    player.speed *= 0.9;
    player.slowTimer = 1.0;

    //visual feedback
    player.setFillStyle(0xffff00);

    // Prevent multiple triggers per second
    this.time.delayedCall(300, () => {
        player.spikeCooldown = false;
        player.setFillStyle(0xff0000);
    });
}
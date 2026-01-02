// Global socket reference
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
const MAX_JUMP_HEIGHT_TILES = 2;
const JUMP_VELOCITY = Math.sqrt(2 * 400 * (MAX_JUMP_HEIGHT_TILES * tileSize));
let mySocketId = null;
let sceneContext = null;

function preload() {
}

function create() {
    sceneContext = this;

    // Create socket connection "http://127.0.0.1:5000",
    gameSocket = io("http://127.0.0.1:5000");

    gameSocket.on("gameOver", (data) => {
        if (this.gameEnded) return;
        this.gameEnded = true;
        game.destroy(true)
        gameSocket.disconnect();
        window.location.href = `/game_over?winner=${data.winnerUsername}&reason=${data.reason}`;
    });

    gameSocket.on("connect", () => {
        mySocketId = gameSocket.id;
        gameSocket.emit("rejoinRoom");

        // request the first chunk
        setTimeout(() => {
            gameSocket.emit('requestChunk', 0);}, 200);
    });

    gameSocket.on("reconnect", () => {
        console.warn("Socket reconnected, rejoining room");
        gameSocket.emit("rejoinRoom");
    });

    platforms = this.physics.add.staticGroup();
    this.chunksLoaded = false;
    this.offset = 0;

    // Handle map chunks
    gameSocket.on('map', (data) => {
        sceneContext.requestingChunk = false;
        chunkWidth = data.map[0].length;
        drawChunk(sceneContext, data.map, chunkOffset);
        chunkOffset++;
        sceneContext.offset = chunkOffset;
        sceneContext.chunksLoaded = true;

        const worldWidth = chunkOffset * chunkWidth * tileSize;
        sceneContext.physics.world.setBounds(0, 0, worldWidth, height);
        sceneContext.cameras.main.setBounds(0, 0, worldWidth, height);
    });

    // Create user player (red square)
    player = this.add.rectangle(100, 450, tilesToPixels(1), tilesToPixels(1), 0xff0000);
    this.physics.add.existing(player);
    player.body.setCollideWorldBounds(true);
    this.physics.add.collider(player, platforms);


    cursors = this.input.keyboard.createCursorKeys();

    // Handle game start
    gameSocket.on('startGame', (data) => {
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
            sceneContext.physics.add.existing(otherPlayer);
            otherPlayer.body.setCollideWorldBounds(true);
            sceneContext.physics.add.collider(otherPlayer, platforms);
        }
    });

    gameSocket.on('syncState', (data) => {
        sceneContext.serverReady = true;
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
        console.log("===========================\n");
    });

    // Store socket reference
    this.gameSocket = gameSocket;
}




function update(time, delta) {
    if (!sceneContext.chunksLoaded || !sceneContext.serverReady) return;
    if (sceneContext.gameEnded) return;

    sceneContext.cameras.main.scrollX += 100 * (delta / 1000);
    if (!player) return;

    // Handle player movement
    if (cursors.left.isDown) {
        player.body.setVelocityX(-60);
    }
    else if (cursors.right.isDown) {
        player.body.setVelocityX(160);
    }
    else {
        player.body.setVelocityX(100);
    }

    if (cursors.up.isDown /*&& player.body.touching.down*/) {
        player.body.setVelocityY(-JUMP_VELOCITY);
    }

    // Request new chunks
    if (player.x > (chunkOffset - 2) * chunkWidth * tileSize && !sceneContext.requestingChunk) {
        sceneContext.requestingChunk = true;
        gameSocket.emit('requestChunk', parseInt(sceneContext.offset));
    }

    // Send my position to server
    if (gameSocket && gameSocket.connected) {
        gameSocket.emit('playerMovement', { x: player.x, y: player.y });


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
                let spike = createSpike(
                    scene,
                    (x + offset * chunk[y].length) * tileSize + tileSize / 2,
                    y * tileSize + tileSize/2
                );
                platforms.add(spike);
        }   }
    }
}


function createSpike(scene, x, y) {
    // Visual triangle
    const spike = scene.add.triangle(
        x, y,
        0, tileSize,
        tileSize, tileSize,
        tileSize / 2, 0,
        0xff0000
    );

    // Physics hitbox
    const hitbox = scene.physics.add.staticImage(x, y, null);
    hitbox.body.setSize(tileSize * 0.8, tileSize * 0.6);
    hitbox.body.setOffset(
        -tileSize * 0.4,
        -tileSize * 0.1
    );

    return hitbox;
}
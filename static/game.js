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
            gravity: { y: 500 },
            debug: false
        }
    },
    scene: {
        preload: preload,
        create: create,
        update: update
    }
};

let game = new Phaser.Game(config);

let player;
let otherPlayer;
let platforms;
let cursors;
let chunkOffset = 0;
let chunkWidth = 20;
const tileSize = 40;
const height = 600;
let mySocketId = null;
let sceneContext = null;

function preload() {
}

function create() {
    sceneContext = this;

    // Create socket connection "http://127.0.0.1:5000",
    gameSocket = io("http://127.0.0.1:5000",{
        withCredentials: true,
        transports: ['websocket', 'polling']
    });

    gameSocket.on("connect", () => {
        console.log("\n=== GAME PAGE SOCKET CONNECTED ===");
        console.log("New Socket ID:", gameSocket.id);
        mySocketId = gameSocket.id;
        console.log("Emitting rejoinRoom...");
        console.log("===================================\n");

        // Rejoin the game room
        gameSocket.emit("rejoinRoom");

        // Also request the first chunk
        setTimeout(() => {
            console.log("Requesting initial chunk...");
            gameSocket.emit('requestChunk', 0);
        }, 200);
    });

    gameSocket.on("connect_error", (error) => {
        console.error("Connection error:", error);
    });

    gameSocket.on("disconnect", () => {
        console.log("Socket disconnected!");
    });

    platforms = this.physics.add.staticGroup();
    this.chunksLoaded = false;
    this.offset = 0;

    // Handle map chunks
    gameSocket.on('map', (data) => {
        console.log("Received map chunk");
        chunkWidth = data.map[0].length;
        drawChunk(sceneContext, data.map, chunkOffset);
        chunkOffset++;
        sceneContext.offset = chunkOffset;
        sceneContext.chunksLoaded = true;

        const worldWidth = chunkOffset * chunkWidth * tileSize;
        sceneContext.physics.world.setBounds(0, 0, worldWidth, height);
        sceneContext.cameras.main.setBounds(0, 0, worldWidth, height);
    });

    // Create my player (red square)
    player = this.add.rectangle(100, 450, 40, 40, 0xff0000);
    this.physics.add.existing(player);
    player.body.setCollideWorldBounds(true);
    this.physics.add.collider(player, platforms);
    console.log("Created RED player (me) at 100, 450");

    cursors = this.input.keyboard.createCursorKeys();

    // Handle game start
    gameSocket.on('startGame', (data) => {
        console.log("\n========== START GAME EVENT ==========");
        console.log("My Socket ID:", mySocketId);
        console.log("Players in game:", JSON.stringify(data.players, null, 2));

        // Find my player data
        const myPlayer = data.players.find(p => p.id === mySocketId);
        const other = data.players.find(p => p.id !== mySocketId);

        if (myPlayer) {
            console.log(" Found my player data:", myPlayer);
            player.x = myPlayer.x;
            player.y = myPlayer.y;
        } else {
            console.warn("✗ Could not find my player in data!");
        }

        // Create the other player (blue square)
        if (other) {
            console.log(" Found other player:", other);
            console.log(" Creating BLUE square at:", other.x, other.y);

            if (otherPlayer) {
                console.log("Destroying existing otherPlayer...");
                otherPlayer.destroy();
            }

            otherPlayer = sceneContext.add.rectangle(other.x, other.y, 40, 40, 0x0000ff);
            sceneContext.physics.add.existing(otherPlayer);
            otherPlayer.body.setCollideWorldBounds(true);
            sceneContext.physics.add.collider(otherPlayer, platforms);

            console.log(" BLUE player created successfully");
        } else {
            console.warn(" No other player found!");
            console.warn("Total players:", data.players.length);
        }
        console.log("======================================\n");
    });

    // Handle other player movement
    gameSocket.on('playerMoved', (data) => {
        // Always log first 10 movements
        if (!gameSocket.moveCount) gameSocket.moveCount = 0;
        gameSocket.moveCount++;

        if (gameSocket.moveCount <= 10) {
            console.log("\n========== PLAYER MOVED EVENT #" + gameSocket.moveCount + " ==========");
            console.log("My Socket ID:", mySocketId);
            console.log("Moving Player ID:", data.id);
            console.log("Position:", data.x, data.y);
            console.log("Is this me?", data.id === mySocketId);
            console.log("otherPlayer exists?", otherPlayer !== null && otherPlayer !== undefined);
        }

        // Double check this isn't our own movement
        if (data.id === mySocketId) {
            if (gameSocket.moveCount <= 10) {
                console.log(" This is MY movement - IGNORING");
                console.log("========================================\n");
            }
            return;
        }

        if (gameSocket.moveCount <= 10) {
            console.log(" This is OTHER player's movement - UPDATING");
        }

        // Create or update other player
        if (!otherPlayer) {
            console.log(" CREATING BLUE player from movement event!");
            otherPlayer = sceneContext.add.rectangle(data.x, data.y, 40, 40, 0x0000ff);
            sceneContext.physics.add.existing(otherPlayer);
            otherPlayer.body.setCollideWorldBounds(true);
            sceneContext.physics.add.collider(otherPlayer, platforms);
            console.log(" BLUE player CREATED!");
        } else {
            if (gameSocket.moveCount <= 10) {
                console.log(" Updating position:", data.x, data.y);
            }
            otherPlayer.x = data.x;
            otherPlayer.y = data.y;
        }

        if (gameSocket.moveCount <= 10) {
            console.log("========================================\n");
        }
    });

    gameSocket.on('playerDisconnected', (data) => {
        console.log("\n=== PLAYER DISCONNECTED ===");
        console.log("Disconnected player ID:", data.id);
        if (otherPlayer && data.id !== mySocketId) {
            otherPlayer.destroy();
            otherPlayer = null;
            console.log("Removed other player");
        }
        console.log("===========================\n");
    });

    // Store socket reference
    this.gameSocket = gameSocket;
    this.movementLogCounter = 0;
}

function update(time, delta) {
    if (!sceneContext.chunksLoaded) return;
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

    if (cursors.up.isDown && player.body.touching.down) {
        player.body.setVelocityY(-330);
    }

    // Request new chunks
    if (player.x > (chunkOffset - 2) * chunkWidth * tileSize) {
        gameSocket.emit('requestChunk', parseInt(sceneContext.offset));
        sceneContext.offset++;
    }

    // Send my position to server
    if (gameSocket && gameSocket.connected) {
        gameSocket.emit('playerMovement', { x: player.x, y: player.y });

        // Log occasionally
        sceneContext.movementLogCounter++;
        if (sceneContext.movementLogCounter === 1 || sceneContext.movementLogCounter % 120 === 0) {
            console.log(" Sending my position:", Math.round(player.x), Math.round(player.y));
        }
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
            }
        }
    }
}
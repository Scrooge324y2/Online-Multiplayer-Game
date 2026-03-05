// --- Constants (no side effects, fine as module-level) ---
const tileSize = 40;
const height = 600;
const MAX_JUMP_HEIGHT_TILES = 3;
const JUMP_VELOCITY = Math.sqrt(2 * 400 * (MAX_JUMP_HEIGHT_TILES * tileSize));
const SPEED_BOOST = 60;
const BACKWARDS_SPEED = 30;
const MAX_SPEED = 260;
const SPEED_INCREASE_PER_SECOND = 2.5;

function tilesToPixels(tiles) {
    return tiles * tileSize;
}

// --- Scene Class ---
class GameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'GameScene' });
        this.player = null;
        this.otherPlayer = null;
        this.platforms = null;
        this.spikes = null;
        this.cursors = null;
        this.chunkOffset = 0;
        this.chunkWidth = 20;
        this.gameSocket = null;
        this.mySocketId = null;
        this.lastSentX = null;
        this.lastSentY = null;
    }

    preload() {}

    create() {
        this.chunksLoaded = false;
        this.requestingChunk = false;
        this.serverReady = false;
        this.initialChunkRequested = false;
        this.gameEnded = false;

        this.gameSocket = io();

        this.gameSocket.on("gameOver", (data) => {
            if (this.gameEnded) return;
            this.gameEnded = true;
            game.destroy(true);
            this.gameSocket.disconnect();
            history.replaceState(null, "", "/play");
            window.location.href = `/game_over?winner=${data.winnerUsername}&reason=${data.reason}`;
        });

        this.gameSocket.on("connect", () => {
            this.mySocketId = this.gameSocket.id;
            this.gameSocket.emit("rejoinRoom");
        });

        this.gameSocket.on("reconnect", () => {
            this.gameSocket.emit("rejoinRoom");
        });

        this.platforms = this.physics.add.staticGroup();
        this.spikes = this.physics.add.staticGroup();

        // Handle map chunks
        this.gameSocket.on('map', (data) => {
            console.log("Received chunk:", this.chunkOffset);
            this.requestingChunk = false;
            this.chunkWidth = data.map[0].length;
            drawChunk(this, data.map, this.chunkOffset);
            this.chunkOffset++;
            this.chunksLoaded = true;

            const worldWidth = this.chunkOffset * this.chunkWidth * tileSize;
            this.physics.world.setBounds(0, 0, worldWidth, height);
            this.cameras.main.setBounds(0, 0, worldWidth, height);
            this.physics.world.colliders.update();
        });

        // Create user player (red square)
        this.player = this.add.rectangle(100, 450, tilesToPixels(1), tilesToPixels(1), 0xff0000);
        this.physics.add.existing(this.player);
        this.player.body.setCollideWorldBounds(true);
        this.playerCollider = this.physics.add.collider(this.player, this.platforms);
        this.player.body.allowSleep = false;
        this.player.baseSpeed = 100;
        this.player.speed = this.player.baseSpeed;
        this.physics.add.overlap(this.player, this.spikes, this.onSpikeHit, null, this);

        this.cursors = this.input.keyboard.createCursorKeys();

        // Handle game start
        this.gameSocket.on('startGame', (data) => {
            this.serverReady = true;
            this.requestInitialChunkOnce();

            const myPlayer = data.players.find(p => p.id === this.mySocketId);
            const other = data.players.find(p => p.id !== this.mySocketId);

            if (myPlayer) {
                this.player.x = myPlayer.x;
                this.player.y = myPlayer.y;
            }

            if (other) {
                if (this.otherPlayer) {
                    this.otherPlayer.destroy();
                }
                this.otherPlayer = this.add.rectangle(other.x, other.y, tilesToPixels(1), tilesToPixels(1), 0x0000ff);
            }
        });

        // Handle other player movement
        this.gameSocket.on("playerMoved", (data) => {
            console.log("Received player movement:");
            if (data.id === this.mySocketId || !this.otherPlayer) return;
            this.otherPlayer.x = data.x;
            this.otherPlayer.y = data.y;
        });

        this.gameSocket.on('playerDisconnected', (data) => {
            if (this.otherPlayer && data.id !== this.mySocketId) {
                this.otherPlayer.destroy();
                this.otherPlayer = null;
            }
        });

        this.gameSocket.on('redirect_to_play', () => {
            sessionStorage.removeItem("loadedBefore");
            sessionStorage.setItem("flashMessage", "You were disconnected from the game.");
            window.location.replace("/play");
        });
    }

    requestInitialChunkOnce() {
        if (this.initialChunkRequested) return;
        this.initialChunkRequested = true;
        this.chunkOffset = 0;
        this.gameSocket.emit('requestChunk', 0);
    }

    onSpikeHit(player, spike) {
        if (player.spikeCooldown) return;

        player.spikeCooldown = true;
        player.speed *= 0.9;
        player.slowTimer = 1.0;
        player.setFillStyle(0xffff00);

        this.time.delayedCall(300, () => {
            player.spikeCooldown = false;
            player.setFillStyle(0xff0000);
        });
    }

    update(time, delta) {
        if (!this.serverReady) return;
        if (!this.chunksLoaded) {
            this.player.body.setVelocityX(0);
            return;
        }
        if (this.gameEnded) return;

        this.cameras.main.startFollow(this.player, true, 0.1, 0.1);

        if (!this.player) return;

        this.player.baseSpeed += SPEED_INCREASE_PER_SECOND * (delta / 1000);
        this.player.baseSpeed = Math.min(this.player.baseSpeed, MAX_SPEED);

        const touchingGround = this.player.body.blocked.down;
        const touchingWall = this.player.body.blocked.left || this.player.body.blocked.right;
        const atBottomOfScreen = this.player.body.bottom >= this.cameras.main.worldView.bottom - 5;
        const jumpPressed = Phaser.Input.Keyboard.JustDown(this.cursors.up);

        let didWallJump = false;

        if (this.player.slowTimer > 0) {
            this.player.slowTimer -= delta / 1000;
            if (this.player.slowTimer <= 0) {
                this.player.speed = this.player.baseSpeed;
            }
        }

        // WALL JUMP
        if (jumpPressed && touchingWall && !this.player.body.blocked.up) {
            this.player.body.setVelocityY(-JUMP_VELOCITY * 0.85);
            const push = this.player.body.blocked.left ? 180 : -180;
            this.player.body.setVelocityX(push);
            didWallJump = true;
        }
        // NORMAL JUMP
        else if (jumpPressed && (touchingGround || atBottomOfScreen)) {
            this.player.body.setVelocityY(-JUMP_VELOCITY);
        }

        if (!didWallJump) {
            if (this.cursors.left.isDown) {
                this.player.body.setVelocityX(this.player.speed - (this.player.speed + BACKWARDS_SPEED));
            } else if (this.cursors.right.isDown) {
                this.player.body.setVelocityX(this.player.speed + SPEED_BOOST);
            } else {
                this.player.body.setVelocityX(this.player.speed);
            }
        }

        if (this.cursors.down.isDown && !touchingGround) {
            this.player.body.setVelocityY(200);
        }

        // Request new chunks
        if (this.player.x > (this.chunkOffset - 2) * this.chunkWidth * tileSize && !this.requestingChunk) {
            this.requestingChunk = true;
            this.gameSocket.emit('requestChunk', parseInt(this.chunkOffset));
        }

        // Send position to server
        if (this.gameSocket && this.gameSocket.connected &&
            (this.player.x !== this.lastSentX || this.player.y !== this.lastSentY)) {
            this.gameSocket.emit('playerMovement', { x: this.player.x, y: this.player.y });
            this.lastSentX = this.player.x;
            this.lastSentY = this.player.y;
        }
    }
}

// --- Helper functions (stateless, receive scene as parameter) ---
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
                scene.platforms.add(plat);
            } else if (chunk[y][x] === 2) {
                const spike = createSpike(
                    scene,
                    (x + offset * chunk[y].length) * tileSize + tileSize / 2,
                    y * tileSize + tileSize / 2
                );
                scene.spikes.add(spike);
            }
        }
    }
    scene.platforms.children.each(p => p.body.updateFromGameObject());
    scene.physics.add.overlap(scene.player, scene.spikes, scene.onSpikeHit, null, scene);
}

function createSpike(scene, x, y) {
    scene.add.triangle(
        x, y,
        0, tileSize,
        tileSize, tileSize,
        tileSize / 2, 0,
        0xff0000
    );

    const hitbox = scene.add.zone(x, y, tileSize * 0.8, tileSize * 0.6);
    scene.physics.add.existing(hitbox, true);
    hitbox.body.updateFromGameObject();
    hitbox.isSpike = true;

    return hitbox;
}

// --- Phaser config ---
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
    scene: GameScene
};

const game = new Phaser.Game(config);
const TILESIZE = 40;
const WORLD_HEIGHT = 600;
const MAX_JUMP_HEIGHT_TILES = 2;
const GRAVITY = 800;
const JUMP_VELOCITY = Math.sqrt(2 * GRAVITY * (MAX_JUMP_HEIGHT_TILES * TILESIZE));

// When the player releases the jump button early, their upward velocity is
// multiplied by this value to cut the jump short, giving a short hop.
const JUMP_CUT_MULTIPLIER = 0.5; //upward velocity is reduced to 50% when jump is released

const SPEED_BOOST = 60;
const BACKWARDS_SPEED = 30;
const MAX_SPEED = 260;
const SPEED_INCREASE_PER_SECOND = 1.5;

function tilesToPixels(tiles) {
    return tiles * TILESIZE;
}


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
        this.myUsername = null;
        this.opponentUsername = null;
        this.jumpBufferTimer = 0;
        this.canDoubleJump = false;
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
            this.requestingChunk = false;
            this.chunkWidth = data.map[0].length;
            drawChunk(this, data.map, this.chunkOffset);
            this.chunkOffset++;
            this.chunksLoaded = true;

            const worldWidth = this.chunkOffset * this.chunkWidth * TILESIZE;
            this.physics.world.setBounds(0, 0, worldWidth, WORLD_HEIGHT);
            this.cameras.main.setBounds(0, 0, worldWidth, WORLD_HEIGHT);
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

            const myPlayer = data.players.find(p => p.sid === this.mySocketId);
            const other = data.players.find(p => p.sid !== this.mySocketId);

            if (myPlayer) {
                this.player.x = myPlayer.x;
                this.player.y = myPlayer.y;
                this.myUsername = myPlayer.username;
                console.log(`You are ${this.myUsername}`);
            }

            if (other) {
                if (this.otherPlayer) {
                    this.otherPlayer.destroy();
                }
                this.otherPlayer = this.add.rectangle(other.x, other.y, tilesToPixels(1), tilesToPixels(1), 0x0000ff);
                this.opponentUsername = other.username;
                console.log(`Opponent is ${this.opponentUsername}`);
            }
        });

        // Handle other player movement
        this.gameSocket.on("playerMoved", (data) => {
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

        this.gameSocket.on('distanceUpdate', (data) => {
            this.distanceAhead = data.distanceAhead;
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
        const jumpReleased = Phaser.Input.Keyboard.JustUp(this.cursors.up);

        let didWallJump = false;

        if (this.player.slowTimer > 0) {
            this.player.slowTimer -= delta / 1000;
            if (this.player.slowTimer <= 0) {
                this.player.speed = this.player.baseSpeed;
            }
        }

        // Restore double jump when landing
        if (touchingGround || atBottomOfScreen) {
            this.canDoubleJump = true;
        }

        // Reduce buffer timer each frame
        if (this.jumpBufferTimer > 0) {
            this.jumpBufferTimer -= delta;
        }

        // When jump is pressed, start the buffer window
        if (jumpPressed) {
            this.jumpBufferTimer = 150; // milliseconds
        }

        // Variable jump height: if the player releases the up key while still
        // moving upward (negative Y velocity), cut the velocity sharply.
        // This gives a short hop on tap and a full jump on hold.
        if (jumpReleased && this.player.body.velocity.y < 0) {
            this.player.body.setVelocityY(this.player.body.velocity.y * JUMP_CUT_MULTIPLIER);
        }

        // WALL JUMP - check jumpPressed directly (instant, no buffer needed)
        if (jumpPressed && touchingWall && !this.player.body.blocked.up) {
            this.player.body.setVelocityY(-JUMP_VELOCITY * 0.85);
            const push = this.player.body.blocked.left ? 180 : -180;
            this.player.body.setVelocityX(push);
            this.jumpBufferTimer = 0;
            didWallJump = true;
        }
        // NORMAL JUMP - consumes the buffer
        else if (this.jumpBufferTimer > 0 && (touchingGround || atBottomOfScreen)) {
            this.player.body.setVelocityY(-JUMP_VELOCITY);
            this.jumpBufferTimer = 0;
        }
        // DOUBLE JUMP - only in the air and only once per landing
        else if (jumpPressed && !touchingGround && !atBottomOfScreen && this.canDoubleJump) {
            this.player.body.setVelocityY(-JUMP_VELOCITY);
            this.canDoubleJump = false;
            this.jumpBufferTimer = 0;
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
        if (this.player.x > (this.chunkOffset - 2) * this.chunkWidth * TILESIZE && !this.requestingChunk) {
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

function drawChunk(scene, chunk, offset) {
    for (let y = 0; y < chunk.length; y++) {
        for (let x = 0; x < chunk[y].length; x++) {
            if (chunk[y][x] === 1) {
                let plat = scene.add.rectangle(
                    (x + offset * chunk[y].length) * TILESIZE + TILESIZE / 2,
                    y * TILESIZE + TILESIZE / 2,
                    TILESIZE,
                    TILESIZE,
                    0x00ff00
                );
                scene.physics.add.existing(plat, true);
                scene.platforms.add(plat);
            } else if (chunk[y][x] === 2) {
                const spike = createSpike(
                    scene,
                    (x + offset * chunk[y].length) * TILESIZE + TILESIZE / 2,
                    y * TILESIZE + TILESIZE / 2
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
        0, TILESIZE,
        TILESIZE, TILESIZE,
        TILESIZE / 2, 0,
        0xff0000
    );

    const hitbox = scene.add.zone(x, y, TILESIZE * 0.8, TILESIZE * 0.6);
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
            gravity: { y: 800 },
            debug: false
        }
    },
    scene: GameScene
};

const game = new Phaser.Game(config);
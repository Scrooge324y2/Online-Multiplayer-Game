const TILESIZE = 40;
const WORLD_HEIGHT = 600;
const MAX_JUMP_HEIGHT_TILES = 2;
const GRAVITY = 800;
const JUMP_VELOCITY = Math.sqrt(2 * GRAVITY * (MAX_JUMP_HEIGHT_TILES * TILESIZE));
const JUMP_CUT_MULTIPLIER = 0.5;
const SPEED_BOOST = 60;
const BACKWARDS_SPEED = 30;
const MAX_SPEED = 260;
const SPEED_INCREASE_PER_SECOND = 0.5;


//Per-biome visual definitions — drives sky, tile and spike appearance.
const BIOME_VISUALS = {
    Plain: {
        skyTop:       0x5ba3d9,
        skyBottom:    0xb8e89a,
        tileColor:    0x4a8c35,
        tileTopColor: 0x72c050,
        ceilingColor: 0x4a8c35,   // (unused in plains, kept for consistency)
        ceilingCapColor: 0x72c050,
        spikeColor:   0xff5522,
        label:        'Plain',
    },
    Hill: {
        skyTop:       0x4a8ebf,
        skyBottom:    0xa0d880,
        tileColor:    0x3d7828,
        tileTopColor: 0x5ca040,
        ceilingColor: 0x3d7828,
        ceilingCapColor: 0x5ca040,
        spikeColor:   0xff4400,
        label:        'Hills',
    },
    Mountain: {
        skyTop:       0x1e2a3a,
        skyBottom:    0x506070,
        tileColor:    0x6a7a80,
        tileTopColor: 0xeef2f8,
        ceilingColor: 0x506070,
        ceilingCapColor: 0x8090a0,
        spikeColor:   0xc8e0ff,
        label:        'Mountains',
    },
    Cave: {
        skyTop:       0x06060f,
        skyBottom:    0x100c1e,
        tileColor:    0x28205a,
        tileTopColor: 0x3e2e70,
        ceilingColor: 0x1a1230,
        ceilingCapColor: 0x2a1e50,
        spikeColor:   0x00ffaa,
        label:        'Cave',
    },
};

//Fallback for unknown biome names
function getBiomeVisuals(biomeName) {
    return BIOME_VISUALS[biomeName] || BIOME_VISUALS.Plain;
}

//Linear colour interpolation helper for progress bar gradient
function lerpColor(c1, c2, t) {
    const r1 = (c1 >> 16) & 0xff, g1 = (c1 >> 8) & 0xff, b1 = c1 & 0xff;
    const r2 = (c2 >> 16) & 0xff, g2 = (c2 >> 8) & 0xff, b2 = c2 & 0xff;
    return ((Math.round(r1 + (r2 - r1) * t) << 16) |
            (Math.round(g1 + (g2 - g1) * t) << 8) |
             Math.round(b1 + (b2 - b1) * t));
}

function tilesToPixels(tiles) { return tiles * TILESIZE; }


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
        this.jumpBufferTimer= 0;
        this.canDoubleJump = false;
        this.currentBiome = 'Plain';
        this.distanceAhead = 0;
        this.chunkBiomes = {};
    }

    preload() {}

    create() {
        this.chunksLoaded = false;
        this.requestingChunk = false;
        this.serverReady = false;
        this.initialChunkRequested = false;
        this.gameEnded = false;


        this.bgGraphics = this.add.graphics().setScrollFactor(0).setDepth(-10);

        this._drawBackground('Plain');

        this.hudGraphics = this.add.graphics().setScrollFactor(0).setDepth(100);

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

        this.gameSocket.on('map', (data) => {
            this.requestingChunk = false;
            this.chunkWidth = data.map[0].length;
            this.chunkBiomes[this.chunkOffset] = data.biome;
            drawChunk(this, data.map, this.chunkOffset, data.biome);
            this.chunkOffset++;
            this.chunksLoaded = true;

            const worldWidth = this.chunkOffset * this.chunkWidth * TILESIZE;
            this.physics.world.setBounds(0, 0, worldWidth, WORLD_HEIGHT);
            this.cameras.main.setBounds(0, 0, worldWidth, WORLD_HEIGHT);
            this.physics.world.colliders.update();
        });

        this.player = this.add.rectangle(100, 450, tilesToPixels(1), tilesToPixels(1), 0xe04040);
        this.physics.add.existing(this.player);
        this.player.body.setCollideWorldBounds(true);
        this.player.body.setSize(TILESIZE, TILESIZE * 0.9); // Slightly shorter hitbox to avoid snagging on ceilings
        this.player.body.setOffset(0, TILESIZE * 0.1); // Center the hitbox vertically on the sprite
        this.playerCollider = this.physics.add.collider(this.player, this.platforms);
        this.player.body.allowSleep = false;
        this.player.baseSpeed = 100;
        this.player.speed = this.player.baseSpeed;
        this.physics.add.overlap(this.player, this.spikes, this.onSpikeHit, null, this);


        //Username tag above the player
        this.playerLabel = this.add.text(100, 450, '', {
            fontSize: '11px', fontFamily: 'Arial',
            color: '#ffffff', stroke: '#000000', strokeThickness: 3,
        }).setOrigin(0.5, 1).setDepth(3);

        //Opponent username tag
        this.opponentLabel = this.add.text(0, 0, '', {
            fontSize: '11px', fontFamily: 'Arial',
            color: '#aabbff', stroke: '#000000', strokeThickness: 3,
        }).setOrigin(0.5, 1).setDepth(3);

        this.cursors = this.input.keyboard.createCursorKeys();

        //HUD — distance text, centred top of screen
        this.distanceText = this.add.text(400, 14, '', {
            fontSize: '21px',
            fontFamily: '"Arial Black", Arial',
            fontStyle: 'bold',
            color: '#ffffff',
            stroke: '#000000',
            strokeThickness: 5,
        }).setScrollFactor(0).setOrigin(0.5, 0).setDepth(101);


        //HUD — progress bar label
        this.progressLabel = this.add.text(400, 574, '', {
            fontSize: '10px', fontFamily: 'Arial',
            color: '#aaaaaa', stroke: '#000000', strokeThickness: 2,
        }).setScrollFactor(0).setOrigin(0.5, 1).setDepth(102);

        //Game start event — receives initial player states and biome, sets up opponent if present
        this.gameSocket.on('startGame', (data) => {
            this.serverReady = true;
            this.winDistancePx = data.winDistance;
            this.winDistanceTiles = Math.round(this.winDistancePx / TILESIZE);
            this.requestInitialChunkOnce();

            const myPlayer = data.players.find(p => p.sid === this.mySocketId);
            const other = data.players.find(p => p.sid !== this.mySocketId);

            if (myPlayer) {
                this.player.x = myPlayer.x;
                this.player.y = myPlayer.y;
                this.myUsername = myPlayer.username;
                this.playerLabel.setText(this.myUsername);
            }

            if (other) {
                if (this.otherPlayer) this.otherPlayer.destroy();
                this.otherPlayer = this.add.rectangle(
                    other.x, other.y, tilesToPixels(1), tilesToPixels(1), 0x4060e8
                );
                this.opponentUsername = other.username;
                this.opponentLabel.setText(this.opponentUsername);

            }
        });

        // Other-player movement updates
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

        //distanceAhead stored for HUD use
        this.gameSocket.on('distanceUpdate', (data) => {
            this.distanceAhead = data.distanceAhead;
        });
    }

    //Redraws the gradient sky whenever the biome changes
    _drawBackground(biomeName) {
        const v = getBiomeVisuals(biomeName);

        // Sky gradient
        this.bgGraphics.clear();
        this.bgGraphics.fillGradientStyle(v.skyTop, v.skyTop, v.skyBottom, v.skyBottom, 1);
        this.bgGraphics.fillRect(0, 0, 800, 600);

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
        player.speed *= 0.5;
        player.slowTimer = 1.0;
        player.setFillStyle(0xffee00);

        this.time.delayedCall(1000, () => {
            player.spikeCooldown = false;
            player.setFillStyle(0xe04040);
        });
    }

    update(time, delta) {
        if (!this.serverReady) return;
        if (!this.chunksLoaded) { this.player.body.setVelocityX(0); return; }
        if (this.gameEnded)     return;

        this.cameras.main.startFollow(this.player, true, 0.1, 0.1);
        if (!this.player) return;

        const currentChunk = Math.floor(this.player.x / (this.chunkWidth * TILESIZE));
        const biome = this.chunkBiomes[currentChunk];

        if (biome && biome !== this.currentBiome) {
            this.currentBiome = biome;
        }

        this.player.baseSpeed += SPEED_INCREASE_PER_SECOND * (delta / 1000);
        this.player.baseSpeed = Math.min(this.player.baseSpeed, MAX_SPEED);

        const touchingGround = this.player.body.blocked.down;
        const touchingWall= this.player.body.blocked.left || this.player.body.blocked.right;
        const atBottomOfScreen = this.player.body.bottom >= this.cameras.main.worldView.bottom - 5;
        const jumpPressed = Phaser.Input.Keyboard.JustDown(this.cursors.up);
        const jumpReleased = Phaser.Input.Keyboard.JustUp(this.cursors.up);

        let didWallJump = false;

        if (this.player.slowTimer > 0) {
            this.player.slowTimer -= delta / 1000;
            if (this.player.slowTimer <= 0) this.player.speed = this.player.baseSpeed;
        }

        if (touchingGround || atBottomOfScreen) this.canDoubleJump = true;
        if (this.jumpBufferTimer > 0) this.jumpBufferTimer -= delta;
        if (jumpPressed) this.jumpBufferTimer = 150;

        if (jumpReleased && this.player.body.velocity.y < 0)
            this.player.body.setVelocityY(this.player.body.velocity.y * JUMP_CUT_MULTIPLIER);

        if (jumpPressed && touchingWall && !this.player.body.blocked.up) {
            this.player.body.setVelocityY(-JUMP_VELOCITY * 0.85);
            const push = this.player.body.blocked.left ? 180 : -180;
            this.player.body.setVelocityX(push);
            this.jumpBufferTimer = 0;
            didWallJump = true;
        } else if (this.jumpBufferTimer > 0 && (touchingGround || atBottomOfScreen)) {
            this.player.body.setVelocityY(-JUMP_VELOCITY);
            this.jumpBufferTimer = 0;
        } else if (jumpPressed && !touchingGround && !atBottomOfScreen && this.canDoubleJump) {
            this.player.body.setVelocityY(-JUMP_VELOCITY);
            this.canDoubleJump = false;
            this.jumpBufferTimer = 0;
        }

        if (!didWallJump) {
            if      (this.cursors.left.isDown)  this.player.body.setVelocityX(-(this.player.speed + BACKWARDS_SPEED - this.player.speed));
            else if (this.cursors.right.isDown) this.player.body.setVelocityX(this.player.speed + SPEED_BOOST);
            else                                this.player.body.setVelocityX(this.player.speed);
        }

        if (this.cursors.down.isDown && !touchingGround)
            this.player.body.setVelocityY(200);

        // Chunk loading
        if (this.player.x > (this.chunkOffset - 2) * this.chunkWidth * TILESIZE && !this.requestingChunk) {
            this.requestingChunk = true;
            this.gameSocket.emit('requestChunk', parseInt(this.chunkOffset));
        }

        // Send position
        if (this.gameSocket && this.gameSocket.connected &&
            (this.player.x !== this.lastSentX || this.player.y !== this.lastSentY)) {
            this.gameSocket.emit('playerMovement', { x: this.player.x, y: this.player.y });
            this.lastSentX = this.player.x;
            this.lastSentY = this.player.y;
        }

        if (this.playerLabel) {
            this.playerLabel.x = this.player.x;
            this.playerLabel.y = this.player.y - TILESIZE / 2 - 4;
        }
        if (this.otherPlayer) {
            if (this.opponentLabel) {
                this.opponentLabel.x = this.otherPlayer.x;
                this.opponentLabel.y = this.otherPlayer.y - TILESIZE / 2 - 4;
            }
        }

        //Redraw HUD every frame
        this._updateHUD();
    }

    //Redraws all HUD elements — distance text, biome label, progress bar
    _updateHUD() {
        //Distance text (top centre)
        if (this.distanceText) {
            const distM = Math.round(Math.abs(this.distanceAhead) / TILESIZE);
            const isAhead = this.distanceAhead > 5;
            const isBehind = this.distanceAhead < -5;

            if (isAhead) {
                this.distanceText.setText(`▲  ${distM}m ahead`);
                this.distanceText.setColor('#44ff66');
            } else if (isBehind) {
                this.distanceText.setText(`▼  ${distM}m behind`);
                this.distanceText.setColor('#ff5555');
            } else {
                this.distanceText.setText('Neck and neck');
                this.distanceText.setColor('#ffffff');
            }
        }

        //Progress bar (bottom)
        if (this.hudGraphics) {
            const ratio = Math.min(1, Math.abs(this.distanceAhead) / this.winDistancePx);
            const barWidth = Math.round(ratio * 396);
            const isAhead= this.distanceAhead > 5;
            const isBehind = this.distanceAhead < -5;

            const barColor = isBehind ? lerpColor(0xffee00, 0xff4444, Math.min(1, ratio * 2))
                           : isAhead  ? lerpColor(0x44ff66, 0xffee00, Math.min(1, ratio * 1.5))
                           :            0x888888;

            this.hudGraphics.clear();

            this.hudGraphics.fillStyle(0x111111, 0.75);
            this.hudGraphics.fillRoundedRect(198, 577, 404, 16, 4);

            if (barWidth > 2) {
                this.hudGraphics.fillStyle(barColor, 0.9);
                this.hudGraphics.fillRoundedRect(200, 579, barWidth, 12, 3);

                // Shine stripe on top of bar
                this.hudGraphics.fillStyle(0xffffff, 0.18);
                this.hudGraphics.fillRect(200, 579, barWidth, 4);
            }

            // Update label
            if (this.progressLabel) {
                const gapM = Math.round(Math.abs(this.distanceAhead) / TILESIZE);
                this.progressLabel.setText(
                    `${gapM}m gap  ·  need ${this.winDistanceTiles}m to win`
                );
            }
        }
    }
}



function drawChunk(scene, chunk, offset, biomeName) {
    const v = getBiomeVisuals(biomeName || 'Plain');

    const chunkPxX = offset * chunk[0].length * TILESIZE;
    const chunkPxW = chunk[0].length * TILESIZE;
    const bgRect = scene.add.graphics().setDepth(-10);
    bgRect.fillGradientStyle(v.skyTop, v.skyTop, v.skyBottom, v.skyBottom, 1);
    bgRect.fillRect(chunkPxX, 0, chunkPxW, WORLD_HEIGHT);

    for (let y = 0; y < chunk.length; y++) {
        for (let x = 0; x < chunk[y].length; x++) {
            const tileVal = chunk[y][x];
            const px = (x + offset * chunk[y].length) * TILESIZE + TILESIZE / 2;
            const py = y * TILESIZE + TILESIZE / 2;

            if (tileVal === 1) {
                const tile = scene.add.rectangle(px, py, TILESIZE, TILESIZE, v.tileColor);
                scene.physics.add.existing(tile, true);
                scene.platforms.add(tile);

                const isTop = (y === 0 || chunk[y - 1][x] === 0);
                if (isTop) {
                    scene.add.rectangle(px, py - TILESIZE / 2 + 3, TILESIZE, 6, v.tileTopColor)
                        .setDepth(1);
                }

            } else if (tileVal === 3) {
                const tile = scene.add.rectangle(px, py, TILESIZE, TILESIZE, v.ceilingColor);
                scene.physics.add.existing(tile, true);
                scene.platforms.add(tile);

                const isBottom = (y === chunk.length - 1 || chunk[y + 1][x] === 0);
                if (isBottom) {
                    scene.add.rectangle(px, py + TILESIZE / 2 - 3, TILESIZE, 6, v.ceilingCapColor)
                        .setDepth(1);
                }

            } else if (tileVal === 2) {
                const spike = createSpike(scene, px, py, v.spikeColor);
                scene.spikes.add(spike);
            }
        }
    }

    scene.platforms.children.each(p => p.body.updateFromGameObject());
    scene.physics.add.overlap(scene.player, scene.spikes, scene.onSpikeHit, null, scene);
}



function createSpike(scene, x, y, color) {
    color = color || 0xff5522;

    scene.add.triangle(
        x, y,
        0,           TILESIZE,
        TILESIZE,    TILESIZE,
        TILESIZE / 2, 0,
        color
    ).setDepth(1);

    if (color === BIOME_VISUALS.Cave.spikeColor) {
        scene.add.circle(x, y - TILESIZE * 0.35, 11, color, 0.28).setDepth(0);
    }

    const hitbox = scene.add.zone(x, y, TILESIZE * 0.6, TILESIZE * 0.6);
    scene.physics.add.existing(hitbox, true);
    hitbox.body.updateFromGameObject();
    hitbox.isSpike = true;
    return hitbox;
}


//Phaser config
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
        arcade: { gravity: { y: 800 }, debug: false }
    },
    scene: GameScene
};

const game = new Phaser.Game(config);
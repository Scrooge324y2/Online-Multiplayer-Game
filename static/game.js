const socket = io();


const config = {
    type: Phaser.AUTO,
    width: 800, // game width
    height: 600, // game height
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    },
    physics: {
        default: 'arcade',
        arcade: {
            gravity: {y: 500 },
            debug: false
        }
    },
    scene: {
        preload: preload,
        create: create,
        update: update
    }
};

let game = new Phaser.Game(config); //creates the game using the config settings

let player;
let platforms;
let cursors;
let chunkOffset = 0; //Number of chunks loaded
let chunkWidth = 20;
const tileSize = 40;
const height = 600;


function preload() {

}

function create() {
    platforms = this.physics.add.staticGroup();

    socket.on('map', (data) => {
        chunkWidth = data.map[0].length; // get the width of the chunk from the first row
        //tileSize = 800 / chunkWidth
        drawChunk(this, data.map, chunkOffset)
        chunkOffset++;

        const worldWidth = chunkOffset * chunkWidth * tileSize;
        this.physics.world.setBounds(0, 0, worldWidth, height);
        this.cameras.main.setBounds(0, 0, worldWidth, height);
    });

    socket.emit('requestChunk');
    player = this.add.rectangle(100, 450, 40, 40, 0xff0000);
    this.physics.add.existing(player);
    player.body.setCollideWorldBounds(true); // prevent player from going out of bounds

    this.physics.add.collider(player, platforms); //collide player with platforms

    cursors = this.input.keyboard.createCursorKeys(); // arrow keys for movement

}

function update(time, delta) {
    this.cameras.main.scrollX += 100 * (delta / 1000); // auto-scroll the camera to the right
    if (!player) return; // Ensure player exists before updating

    if (cursors.left.isDown) {
        player.body.setVelocityX(-60);
    }
    else if (cursors.right.isDown) {
        player.body.setVelocityX(160);
    }
    else {
        player.body.setVelocityX(100);
    }

    if (cursors.up.isDown && player.body.touching.down) { //if up key is pressed and player is touching the ground
        player.body.setVelocityY(-330);
    }
    if (player.x > (chunkOffset - 2) * chunkWidth * tileSize) { // if player is near the right edge of the current chunk
        socket.emit('requestChunk');
    }

}

//loops through mapData, wherever value is 1, create a square platform
function drawChunk(scene, chunk, offset) {
    console.log(chunk)
    for (let y = 0; y< chunk.length; y++) { //loops through chunk array
        for (let x = 0; x < chunk[y].length; x++) {
            if (chunk[y][x] === 1){
                let plat = scene.add.rectangle((x + offset * chunk[y].length) * tileSize + tileSize / 2, y*tileSize + tileSize / 2, tileSize, tileSize, 0x00ff00);
                scene.physics.add.existing(plat, true); // make the platform a physics object
                platforms.add(plat); // add the platform to the static group
            }
        }
    }

}
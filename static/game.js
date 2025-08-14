window.addEventListener('load', () => {  //waits for page to load before running code
    const socket = io();
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    let tileSize = 32;
    let map = [];

    function resizeCanvas() { // Resizes the canvas to fit the window
        let aspectRatio = 16 / 9;

        if (window.innerWidth / window.innerHeight <= aspectRatio) {
            canvas.width = window.innerWidth;
            canvas.height = canvas.width / aspectRatio;

        } else {
            canvas.height = window.innerHeight;
            canvas.width = canvas.height * aspectRatio;
        }
        tileSize = canvas.width/ map.length
        drawMap();
    }

    window.addEventListener('resize', resizeCanvas);

    socket.on('map', (data) => { //receives the map data from the server and draws it on the canvas
        map = data.map;
        tileSize = canvas.width/ map.length
        resizeCanvas();
        drawMap();
        console.log('hello from client');
    });

    function drawMap() {
        console.log('hello world')
        console.log(map)
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (let x = 0; x < map.length; x++) {
            for (let y = 0; y < map[x].length; y++) {
                if (map[x][y] === 1) {
                    ctx.fillStyle = 'black';
                    ctx.fillRect(x * tileSize, y * tileSize, tileSize, tileSize);
                }
            }
        }
    }
});



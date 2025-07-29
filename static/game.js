window.addEventListener('load', () => {
    const socket = io();
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const tileSize = 32;
    let map = [];

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        //drawMap();
    }

    window.addEventListener('resize', resizeCanvas);

    socket.on('map', (data) => {
        map = data.map;
        resizeCanvas();
        drawMap();
    });

    function drawMap() {
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



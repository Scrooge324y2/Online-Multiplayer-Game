

def generate_terrain(chunkWidth=20, tileSize=40, offset=0):
    from opensimplex import OpenSimplex
    noise = OpenSimplex(12)

    platforms = []
    for x in range(chunkWidth):
        n = noise.noise2(x=(x+offset) * 0.1, y=0)
        n = (n + 1) / 2  # Normalize to [0, 1]

        height = int(n * 5) #Number of tiles high
        platforms.append(height)
    return platforms

'''def generate_chunk(width=20, height=15, offset=0):
    chunk = [[0 for x in range(width)] for y in range(height)]

    for x in range(width):
        terrainHeight = generate_terrain(chunkWidth=width, offset=offset)[x]
        for y in range(height-1, height-terrainHeight-1, -1):
            chunk[y][x] = 1
    return chunk'''

def generate_chunk(width=20, height=15, offset=0):
    chunk = [[0 for x in range(width)] for y in range(height)]

    # Choose a fixed terrain height (e.g., half the total height)
    terrain_height = 1

    for x in range(width):
        for y in range(height - 1, height - terrain_height - 1, -1):
            chunk[y][x] = 1

    return chunk
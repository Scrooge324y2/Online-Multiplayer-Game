from opensimplex import OpenSimplex

def should_spawn(noise, global_x, y_seed, probability):
    noise_val = noise.noise2(x=global_x * 0.2, y=y_seed)
    normalised = (noise_val + 1) / 2  # Normalise to [0, 1]
    return normalised < probability


def generate_terrain(chunkWidth=20, tileSize=40, offset=0, seed=12):
    noise = OpenSimplex(seed)
    platforms = []
    for x in range(chunkWidth):
        n = noise.noise2(x=(x+offset) * 0.1, y=0)
        n = (n + 1) / 2  # Normalise to [0, 1]

        height = int(n * 5) #Number of tiles high
        platforms.append(height)
    return platforms


def add_floating_platforms(chunk, terrain_heights, width, height, offset, seed):
    if offset == 0:
        return

    noise = OpenSimplex(seed + 1000)

    x = 0
    while x < width:
        global_x = x + offset * width

        if should_spawn(noise, global_x, y_seed=500, probability = 0.3):
            base_height = terrain_heights[x]

            height_noise = abs(noise.noise2(x=(x + offset * width) * 0.15, y=600))
            height_above = 3 + int(height_noise * 3)  # 3 to 6 tiles

            # Platform width 2-4 tiles
            width_noise = abs(noise.noise2(x=(x + offset * width) * 0.25, y=700))
            plat_width = 2 + int(width_noise * 2)  # 2 to 4 tiles

            # Calculate y position in chunk
            platform_y = base_height + height_above

            # Convert to array index (from bottom to top)
            y_index = height - 1 - platform_y

            # Place platform if it fits
            if 0 <= y_index < height and x + plat_width <= width:
                for dx in range(plat_width):
                    chunk[y_index][x + dx] = 1
                x += plat_width  # Skip past this platform
            else:
                x += 1
        else:
            x += 1



def generate_chunk(width=20, height=15, offset=0, seed=12):
    chunk = [[0 for x in range(width)] for y in range(height)]
    terrain_heights = generate_terrain(chunkWidth=width, tileSize=height, offset=offset, seed=seed)


    for x in range(width):
        terrainHeight = terrain_heights[x]
        for y in range(height-1, height-terrainHeight-1, -1):
            chunk[y][x] = 1

    add_floating_platforms(chunk, terrain_heights, width, height, offset, seed)
    return chunk



def generate_flat_chunk(width=20, height=15, offset=0, seed=12): # Generates a flat terrain chunk
    chunk = [[0 for x in range(width)] for y in range(height)]

    # Choose a fixed terrain height (e.g., half the total height)
    terrain_height = 1

    for x in range(width):
        for y in range(height - 1, height - terrain_height - 1, -1):
            chunk[y][x] = 1

    return chunk



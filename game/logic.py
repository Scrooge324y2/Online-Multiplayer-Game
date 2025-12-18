from opensimplex import OpenSimplex
GAP_FREQUENCY =  0.8#0.35               # 0.0 = no gaps, 1.0 = many gaps
FLAT_AREA_FREQUENCY = 0.25         # Controls flat sections
FLOATING_PLATFORM_FREQUENCY = 1 #0.6  # How often platforms appear in gaps
PLATFORMS_ABOVE_FLATS = 0.15       # Chance of platforms above flat areas
FLOATING_PLATFORM_DENSITY = 1  # chance per x column
MIN_PLATFORM_HEIGHT = 3           # tiles above ground
MAX_PLATFORM_HEIGHT = 7
PLATFORM_WIDTH_MIN = 2
PLATFORM_WIDTH_MAX = 4
def generate_terrain(chunkWidth=20, tileSize=40, offset=0, seed=12):
    from opensimplex import OpenSimplex
    noise = OpenSimplex(seed)

    platforms = []
    for x in range(chunkWidth):
        n = noise.noise2(x=(x+offset) * 0.1, y=0)
        n = (n + 1) / 2  # Normalise to [0, 1]

        height = int(n * 5) #Number of tiles high
        platforms.append(height)
    return platforms

def generate_chunk(width=20, height=15, offset=0, seed=12):
    chunk = [[0 for x in range(width)] for y in range(height)]

    for x in range(width):
        terrainHeight = generate_terrain(chunkWidth=width, offset=offset, seed=seed)[x]
        for y in range(height-1, height-terrainHeight-1, -1):
            chunk[y][x] = 1
    return chunk

def generate_flat_chunk(width=20, height=15, offset=0, seed=12): # Generates a flat terrain chunk
    chunk = [[0 for x in range(width)] for y in range(height)]

    # Choose a fixed terrain height (e.g., half the total height)
    terrain_height = 1

    for x in range(width):
        for y in range(height - 1, height - terrain_height - 1, -1):
            chunk[y][x] = 1

    return chunk


'''def generate_terrain(chunkWidth=20, offset=0, seed=12):
    """
    Generate varied terrain with flat areas, drops, and peaks.
    Returns list of terrain heights for each x position.
    """
    noise = OpenSimplex(seed)
    platforms = []

    # Use multiple noise layers for more varied terrain
    for x in range(chunkWidth):
        global_x = x + offset * chunkWidth#convert local x to global x for noise continuity

        n1 = noise.noise2(x=global_x * 0.08, y=0)# Primary noise - larger features
        n2 = noise.noise2(x=global_x * 0.3, y=100) # Secondary noise - adds variation
        combined = (n1 * 0.7 + n2 * 0.3)# Combine noises with weights

        # Normalize to [0, 1]
        combined = (combined + 1) / 2
        height = int(combined * 8)

        # Randomly create flat areas (20% chance)
        if trigger_item(noise, 0.2, global_x):
            # Look at previous height to create flat sections
            if platforms and abs(platforms[-1] - height) <= 1:
                height = platforms[-1]

        platforms.append(height)
    print(f"Terrain heights: {platforms}")
    return platforms

def trigger_item(noise,frequency, global_x):
    noise_val = noise.noise2(x=global_x, y=5000)
    return abs(noise_val)  <= frequency * 2


def generate_floating_platforms(heights, width, height, seed, offset):
    platforms = []
    noise = OpenSimplex(seed + 3000)

    x = 0
    while x < width:
        global_x = x + offset * width


        # Decide if a platform spawns here
        if trigger_item(noise, FLOATING_PLATFORM_FREQUENCY, global_x):
            base_height = heights[x]

            platform_y = base_height + MIN_PLATFORM_HEIGHT + int(
                abs(noise.noise2(x=global_x * 0.15, y=1100))
                * (MAX_PLATFORM_HEIGHT - MIN_PLATFORM_HEIGHT)
            )

            platform_width = PLATFORM_WIDTH_MIN + int(
                abs(noise.noise2(x=global_x * 0.25, y=1200))
                * (PLATFORM_WIDTH_MAX - PLATFORM_WIDTH_MIN)
            )

            # Ensure platform fits horizontally
            if x + platform_width < width:
                platforms.append({
                    "x": x + platform_width // 2,
                    "y": platform_y,
                    "width": platform_width
                })
                x += platform_width + 1
                continue

    x += 1
    print(f"Floating platforms: {platforms}")
    return platforms


def generate_chunk(width=20, height=15, offset=0, seed=12):
    print('generating chunk...')
    if offset == 0:
        return generate_flat_chunk(width, height, offset, seed)

    chunk = [[0 for x in range(width)] for y in range(height)]

    # Generate base terrain
    terrain_heights = generate_terrain(chunkWidth=width, offset=offset, seed=seed)

    # Fill in ground terrain
    for x in range(width):
        terrain_height = terrain_heights[x]
        for y in range(height - 1, height - terrain_height - 1, -1):
            if y >= 0:
                chunk[y][x] = 1
    print(chunk)


    floating_platforms = generate_floating_platforms(terrain_heights,width,height,seed,offset)
    print(f"floating_platforms: {floating_platforms}")
    for platform in floating_platforms:
        center_x = platform["x"]
        width = platform["width"]
        y_world = platform["y"]
        print(f"Platform: {platform['x']}, {platform['y']}")

        chunk_y = height - 1 - y_world
        if not (0 <= chunk_y < height):
            print("continue")
            continue

        for dx in range(width):
            x_pos = center_x - width // 2 + dx
            if 0 <= x_pos < width:
                chunk[chunk_y][x_pos] = 1
    print(f"Chunk: {chunk}")
    return chunk'''
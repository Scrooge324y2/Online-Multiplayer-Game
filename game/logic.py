from opensimplex import OpenSimplex
import random
from collections import deque

TILE_SIZE = 1  # logic works in tiles, not pixels

PLAYER_MAX_JUMP_HEIGHT = 2      # tiles
PLAYER_MAX_JUMP_DISTANCE = 4    # tiles

MAX_PLATFORM_HEIGHT_ABOVE = 6
MIN_PLATFORM_HEIGHT_ABOVE = 3




class BiomeType:
    PLAINS = "plains"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    CAVES = "caves"


class ObstacleType:
    SPIKE = 2
    MOVING_PLATFORM = 3
    DISAPPEARING_BLOCK = 4
    BOUNCE_PAD = 5


class ProceduralGenerator:
    def __init__(self, seed=12):
        self.seed = seed
        self.terrain_noise = OpenSimplex(seed)
        self.biome_noise = OpenSimplex(seed + 1000)
        self.obstacle_noise = OpenSimplex(seed + 2000)

    def generate_flat_chunk(self, width=20, height=15, offset=0, seed=12):  # Generates a flat terrain chunk
        chunk = [[0 for x in range(width)] for y in range(height)]

        # Choose a fixed terrain height (e.g., half the total height)
        terrain_height = 1

        for x in range(width):
            for y in range(height - 1, height - terrain_height - 1, -1):
                chunk[y][x] = 1

        return chunk

    def is_jump_possible(self, from_y, to_y, dx):
        """
        Checks if the player can jump from one surface to another.

        from_y: starting surface height (tiles)
        to_y: landing surface height (tiles)
        dx: horizontal distance (tiles)
        """

        dy = to_y - from_y

        if dx > PLAYER_MAX_JUMP_DISTANCE:
            return False

        if dy > PLAYER_MAX_JUMP_HEIGHT:
            return False


        return True

    def determine_biome(self, global_x):
        """
        Determine biome type based on position using noise.
        Creates natural transitions between biomes.
        """
        biome_value = self.biome_noise.noise2(x=global_x * 0.01, y=0)
        biome_value = (biome_value + 1) / 2  # Normalize to [0, 1]

        if biome_value < 0.25:
            return BiomeType.PLAINS
        elif biome_value < 0.5:
            return BiomeType.HILLS
        elif biome_value < 0.75:
            return BiomeType.MOUNTAINS
        else:
            return BiomeType.CAVES

    def get_biome_config(self, biome):
        """
        Return configuration parameters for each biome type.
        Different biomes have different terrain characteristics.
        """
        configs = {
            BiomeType.PLAINS: {
                'height_multiplier': 3,
                'height_variation': 0.1,
                'platform_probability': 0.2,
                'obstacle_probability': 1,
                'gap_probability': 0.1
            },
            BiomeType.HILLS: {
                'height_multiplier': 5,
                'height_variation': 0.15,
                'platform_probability': 0.3,
                'obstacle_probability': 0.25,
                'gap_probability': 0.15
            },
            BiomeType.MOUNTAINS: {
                'height_multiplier': 8,
                'height_variation': 0.2,
                'platform_probability': 0.4,
                'obstacle_probability': 0.3,
                'gap_probability': 0.2
            },
            BiomeType.CAVES: {
                'height_multiplier': 4,
                'height_variation': 0.1,
                'platform_probability': 0.5,
                'obstacle_probability': 0.2,
                'gap_probability': 0.05,
                'has_ceiling': True
            }
        }
        return configs.get(biome, configs[BiomeType.PLAINS])



    def generate_terrain_heights(self, width, offset, biome_config):
        """
        Generate base terrain heights with multiple octaves of noise.
        Uses fractal Brownian motion for more natural-looking terrain.
        """
        heights = []

        for x in range(width):
            global_x = x + offset * width

            noise_val = self.terrain_noise.noise2(x=global_x * 0.15, y=0)
            noise_val = (noise_val + 1) / 2
            height = max(1, int(noise_val * biome_config['height_multiplier'])) # Ensure minimum height of 1
            step_size = 2
            height = (height // step_size) * step_size
            heights.append(height)

        return heights




    def generate_gaps(self, heights, width, offset, biome_config):
        """
        Create gaps in terrain that players must jump over.
        Uses spacing algorithm to prevent impossible sections.
        """
        gaps = []
        min_spacing = 5  # Minimum tiles between gaps
        last_gap_end = -min_spacing

        x = 0
        while x < width:
            global_x = x + offset * width

            # Check if we can place a gap here
            if x - last_gap_end >= min_spacing:
                noise_val = self.obstacle_noise.noise2(x=global_x * 0.3, y=100)
                noise_val = (noise_val + 1) / 2

                if noise_val < biome_config['gap_probability']:
                    # Determine gap width (2-4 tiles)
                    gap_width = 2 + int(abs(self.obstacle_noise.noise2(x=global_x * 0.25, y=200)) * 2)

                    # Ensure gap is jumpable based on height difference
                    if x + gap_width < width:
                        height_before = heights[x]
                        height_after = heights[min(x + gap_width, width - 1)]
                        height_diff = abs(height_before - height_after)

                        # Only create gap if height difference is reasonable
                        if self.is_jump_possible(height_before, height_after, gap_width):
                            gaps.append((x, gap_width))
                            last_gap_end = x + gap_width
                            x += gap_width
                            continue
                x += 1

        return gaps

    def validate_platform_chain(self, heights, platforms, width):
        """
        Ensures there is at least one reachable surface
        for every column in the chunk.
        """

        surfaces = {x: [] for x in range(width)}

        # Ground surfaces
        for x in range(width):
            surfaces[x].append(heights[x])

        # Platform surfaces
        for p in platforms:
            for dx in range(p["width"]):
                px = p["x"] + dx
                if 0 <= px < width:
                    surfaces[px].append(p["y"])

        reachable = {0: surfaces[0]}

        for x in range(1, width):
            reachable[x] = []
            for prev_y in reachable[x - 1]:
                for curr_y in surfaces[x]:
                    if self.is_jump_possible(prev_y, curr_y, 1):
                        reachable[x].append(curr_y)

            if not reachable[x]:
                return False

        return True

    def generate_floating_platforms(self, heights, width, height, offset, biome_config):
        """
        Generate floating platforms with intelligent placement.
        Ensures platforms are reachable and serve a purpose.
        """
        platforms = []
        x = 0

        while x < width:
            global_x = x + offset * width

            noise_val = self.obstacle_noise.noise2(x=global_x * 0.2, y=500)
            noise_val = (noise_val + 1) / 2

            if noise_val < biome_config['platform_probability']:
                base_height = heights[x]

                # Platform height above terrain (3-6 tiles)
                height_noise = abs(self.terrain_noise.noise2(x=global_x * 0.15, y=600))
                height_above = height_above = MIN_PLATFORM_HEIGHT_ABOVE + int(height_noise * (MAX_PLATFORM_HEIGHT_ABOVE - MIN_PLATFORM_HEIGHT_ABOVE))

                # Platform width (2-5 tiles)
                width_noise = abs(self.terrain_noise.noise2(x=global_x * 0.25, y=700))
                plat_width = 2 + int(width_noise * 3)

                platform_y = base_height + height_above

                # Check if platform is within bounds and not too high
                if platform_y < height - 2 and x + plat_width <= width:
                    platforms.append({
                        'x': x,
                        'y': platform_y,
                        'width': plat_width,
                        'type': 'static'
                    })
                    x += plat_width
                else:
                    x += 1
            else:
                x += 1

        return platforms

    # ===== OBSTACLE GENERATION =====

    def generate_obstacles(self, heights, width, offset, biome_config):
        """
        Place obstacles on terrain using weighted probability.
        Different obstacle types based on terrain features.
        """
        obstacles = []

        for x in range(width):
            global_x = x + offset * width

            noise_val = self.obstacle_noise.noise2(x=global_x * 0.4, y=800)
            noise_val = (noise_val + 1) / 2

            if noise_val < biome_config['obstacle_probability']:
                terrain_height = heights[x]

                # Weighted obstacle type selection
                type_noise = abs(self.obstacle_noise.noise2(x=global_x * 0.3, y=900))

                if type_noise < 0.4:
                    obstacle_type = ObstacleType.SPIKE
                elif type_noise < 0.7:
                    obstacle_type = ObstacleType.DISAPPEARING_BLOCK
                else:
                    obstacle_type = ObstacleType.BOUNCE_PAD

                obstacles.append({
                    'x': x,
                    'y': terrain_height,
                    'type': obstacle_type
                })

        return obstacles

    # ===== CAVE GENERATION =====

    def generate_cave_ceiling(self, width, offset):
        """
        Generate ceiling for cave biomes.
        Uses inverted terrain generation.
        """
        ceiling = []

        for x in range(width):
            global_x = x + offset * width

            noise_val = self.terrain_noise.noise2(x=global_x * 0.12, y=1000)
            noise_val = (noise_val + 1) / 2

            # Ceiling height from top (2-5 tiles down)
            ceiling_height = 2 + int(noise_val * 3)
            ceiling.append(ceiling_height)

        return ceiling

    # ===== MAIN GENERATION FUNCTION =====

    def generate_chunk(self, width=20, height=15, offset=0):
        """
        Main chunk generation with all features integrated.
        Returns a 2D array representing the chunk.
        """
        if offset == 0:
            return self.generate_flat_chunk(width, height, offset, self.seed)


        chunk = [[0 for _ in range(width)] for _ in range(height)]

        # Determine biome for this chunk
        chunk_centre_x = offset * width + width // 2
        biome = self.determine_biome(chunk_centre_x)
        biome_config = self.get_biome_config(biome)

        # Generate base terrain
        heights = self.generate_terrain_heights(width, offset, biome_config)

        # Fill in base terrain
        for x in range(width):
            terrain_height = heights[x]
            for y in range(height - 1, height - terrain_height - 1, -1):
                if 0 <= y < height:
                    chunk[y][x] = 1

        # Generate and apply gaps
        gaps = self.generate_gaps(heights, width, offset, biome_config)
        for gap_x, gap_width in gaps:
            for x in range(gap_x, min(gap_x + gap_width, width)):
                for y in range(height):
                    chunk[y][x] = 0  # Clear gap

        # Add floating platforms
        platforms = self.generate_floating_platforms(heights, width, height, offset, biome_config)

        if not self.validate_platform_chain(heights, platforms, width):
            return self.generate_chunk(width, height, offset)

        for platform in platforms:
            plat_y = height - 1 - platform['y']
            if 0 <= plat_y < height:
                for dx in range(platform['width']):
                    if platform['x'] + dx < width:
                        chunk[plat_y][platform['x'] + dx] = 1

        # Add obstacles (represented as different tile values)
        obstacles = self.generate_obstacles(heights, width, offset, biome_config)
        for obstacle in obstacles:
            obs_y = height - 1 - obstacle['y'] - 1  # Place on top of terrain
            if not (0 <= obs_y < height and obstacle['x'] < width):
                continue

            if chunk[obs_y + 1][x] != 1  and obstacle['type'] == ObstacleType.SPIKE: #Ensure spike is only placed on a platform
                continue

            chunk[obs_y][obstacle['x']] = obstacle['type']

        # Add cave ceiling if in cave biome
        if biome == BiomeType.CAVES:
            ceiling_heights = self.generate_cave_ceiling(width, offset)
            for x in range(width):
                for y in range(ceiling_heights[x]):
                    chunk[y][x] = 1

        return chunk



'''
    def validate_chunk_traversable(self, chunk, width, height):
        """
        Uses BFS to verify that a player can traverse from the leftmost column
        to the rightmost column of the chunk, respecting movement constraints.

        Player movement rules:
        - Can only jump from ground (not mid-air)
        - Jump is fixed arc: PLAYER_MAX_JUMP_HEIGHT up, PLAYER_MAX_JUMP_DISTANCE forward
        - Cannot change direction or control jump once airborne
        - Falls straight down (with gravity) when walking off edges

        Returns: (bool, set) - (is_traversable, reachable_positions)
        """

        def get_ground_level(x):
            """Find the topmost solid tile in column x (player stands on top of it)"""
            for y in range(height):
                if chunk[y][x] == 1:
                    return y - 1  # Player stands one tile above solid ground
            return None

        def is_solid(x, y):
            """Check if position has a solid tile"""
            if not (0 <= x < width and 0 <= y < height):
                return False
            return chunk[y][x] == 1

        def is_valid_position(x, y):
            """Check if player can exist at this position (in air or on ground)"""
            if not (0 <= x < width and 0 <= y < height):
                return False
            # Player can't be inside solid blocks
            if is_solid(x, y):
                return False

            if chunk[y][x] == 2:
                return False  # Spike - instant death
            return True

        def simulate_jump(start_x, start_y, direction):
            """
            Simulate a complete jump arc from start position.
            Returns landing position or None if jump is blocked.

            direction: 1 for right, -1 for left
            """
            # Jump follows a parabolic arc
            # Max height reached at PLAYER_MAX_JUMP_DISTANCE / 2
            path = []

            for dist in range(1, PLAYER_MAX_JUMP_DISTANCE + 1):
                x = start_x + (dist * direction)

                if not (0 <= x < width):
                    break  # Out of bounds

                # Parabolic height calculation
                # Peak at middle of jump distance
                progress = dist / PLAYER_MAX_JUMP_DISTANCE
                # Arc formula: goes up then down
                height_offset = int(PLAYER_MAX_JUMP_HEIGHT * (4 * progress * (1 - progress)))
                y = start_y - height_offset

                if not is_valid_position(x, y):
                    break  # Hit obstacle during jump

                path.append((x, y))

            if not path:
                return None

            # From last valid position in arc, fall straight down
            last_x, last_y = path[-1]
            land_y = last_y

            while land_y < height - 1 and not is_solid(last_x, land_y + 1):
                land_y += 1
                if not is_valid_position(last_x, land_y):
                    return None  # Hit something while falling

            if land_y >= height:
                return None  # Fell off map

            return (last_x, land_y)

        def get_neighbors(x, y):
            """
            Get all reachable positions from (x, y).
            Only ground-based movement allowed.
            """
            neighbors = []

            # Check if standing on solid ground
            on_ground = is_solid(x, y + 1)

            if not on_ground:
                # If in air, can only fall straight down
                fall_y = y
                while fall_y < height - 1 and not is_solid(x, fall_y + 1):
                    fall_y += 1
                if fall_y < height and is_valid_position(x, fall_y):
                    neighbors.append((x, fall_y))
                return neighbors

            # On ground - can walk or jump

            # Walk left
            if x > 0 and is_valid_position(x - 1, y):
                if is_solid(x - 1, y + 1):
                    # Ground continues
                    neighbors.append((x - 1, y))
                else:
                    # Walk off edge - fall straight down
                    fall_y = y
                    while fall_y < height - 1 and not is_solid(x - 1, fall_y + 1):
                        fall_y += 1
                    if fall_y < height:
                        neighbors.append((x - 1, fall_y))

            # Walk right
            if x < width - 1 and is_valid_position(x + 1, y):
                if is_solid(x + 1, y + 1):
                    # Ground continues
                    neighbors.append((x + 1, y))
                else:
                    # Walk off edge - fall straight down
                    fall_y = y
                    while fall_y < height - 1 and not is_solid(x + 1, fall_y + 1):
                        fall_y += 1
                    if fall_y < height:
                        neighbors.append((x + 1, fall_y))

            # Jump right (fixed arc)
            jump_landing = simulate_jump(x, y, direction=1)
            if jump_landing:
                neighbors.append(jump_landing)

            # Jump left (fixed arc)
            jump_landing = simulate_jump(x, y, direction=-1)
            if jump_landing:
                neighbors.append(jump_landing)

            return neighbors

        # Find starting position (leftmost ground)
        start_x = 0
        start_y = get_ground_level(start_x)

        if start_y is None or start_y < 0:
            return False, set()  # No valid starting position

        # BFS
        queue = deque([(start_x, start_y)])
        visited = {(start_x, start_y)}
        reached_end = False

        while queue:
            x, y = queue.popleft()

            # Check if we reached the rightmost column
            if x >= width - 1:
                reached_end = True
                # Continue to map all reachable positions, don't break

            # Explore neighbors
            for next_x, next_y in get_neighbors(x, y):
                if (next_x, next_y) not in visited:
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))

        # Check if any position in the last column is reachable
        last_column_reachable = any(x >= width - 1 for x, y in visited)

        return last_column_reachable, visited


    # Add this method to the ProceduralGenerator class
    def validate_and_regenerate(self, width=20, height=15, offset=0, max_attempts=5):
        """
        Generate a chunk and validate it's traversable.
        Regenerate with different parameters if validation fails.

        Returns: valid chunk
        """
        for attempt in range(max_attempts):
            chunk = self.generate_chunk(width, height, offset)
            is_valid, reachable = self.validate_chunk_traversable(chunk, width, height)

            if is_valid:
                return chunk

            # Modify seed slightly for retry
            self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 100)

        # If all attempts fail, return a simplified flat chunk
        print(f"Warning: Could not generate valid chunk after {max_attempts} attempts, returning flat chunk")'''

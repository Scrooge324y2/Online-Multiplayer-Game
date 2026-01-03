from opensimplex import OpenSimplex
from collections import deque
import time

TILE_SIZE = 1
PLAYER_MAX_JUMP_HEIGHT = 2
PLAYER_MAX_JUMP_DISTANCE = 4
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

    def generate_flat_chunk(self, width=20, height=15, offset=0, seed=12):
        chunk = [[0 for x in range(width)] for y in range(height)]
        terrain_height = 1
        for x in range(width):
            for y in range(height - 1, height - terrain_height - 1, -1):
                chunk[y][x] = 1
        return chunk

    def is_jump_possible(self, from_y, to_y, dx):
        dy = to_y - from_y
        if dx > PLAYER_MAX_JUMP_DISTANCE:
            return False
        if dy > PLAYER_MAX_JUMP_HEIGHT:
            return False
        return True

    def determine_biome(self, global_x):
        biome_value = self.biome_noise.noise2(x=global_x * 0.01, y=0)
        biome_value = (biome_value + 1) / 2
        if biome_value < 0.25:
            return BiomeType.PLAINS
        elif biome_value < 0.5:
            return BiomeType.HILLS
        elif biome_value < 0.75:
            return BiomeType.MOUNTAINS
        else:
            return BiomeType.CAVES
        return BiomeType.CAVES

    def get_biome_config(self, biome):
        configs = {
            BiomeType.PLAINS: {
                'height_multiplier': 5,
                'height_variation': 0.2,
                'platform_probability': 0.35,
                'obstacle_probability': 0.12,
                'gap_probability': 0.2,
                'spike_probability': 0.4  # High spike frequency
            },
            BiomeType.HILLS: {
                'height_multiplier': 7,
                'height_variation': 0.25,
                'platform_probability': 0.4,
                'obstacle_probability': 0.15,
                'gap_probability': 0.25,
                'spike_probability': 0.5
            },
            BiomeType.MOUNTAINS: {
                'height_multiplier': 9,
                'height_variation': 0.3,
                'platform_probability': 0.5,
                'obstacle_probability': 0.18,
                'gap_probability': 0.3,
                'spike_probability': 0.6
            },
            BiomeType.CAVES: {
                'height_multiplier': 6,
                'height_variation': 0.2,
                'platform_probability': 0.6,
                'obstacle_probability': 0.15,
                'gap_probability': 0.15,
                'has_ceiling': True,
                'spike_probability': 0.45
            }
        }
        return configs.get(biome, configs[BiomeType.PLAINS])

    def generate_terrain_heights(self, width, offset, biome_config):
        heights = []
        for x in range(width):
            global_x = x + offset * width

            # Multiple octaves for more variation
            noise_val = self.terrain_noise.noise2(x=global_x * 0.1, y=0)  # Base terrain
            detail = self.terrain_noise.noise2(x=global_x * 0.3, y=100) * 0.3  # Detail layer
            noise_val = (noise_val + detail + 1) / 2  # Combine and normalize

            height = max(1, int(noise_val * biome_config['height_multiplier']))
            # Allow single-tile steps for more variation
            heights.append(height)
        return heights

    def generate_gaps(self, heights, width, offset, biome_config):
        gaps = []
        min_spacing = 4  # Allow gaps closer together
        last_gap_end = -min_spacing
        x = 0
        while x < width:
            global_x = x + offset * width
            if x - last_gap_end >= min_spacing:
                noise_val = self.obstacle_noise.noise2(x=global_x * 0.3, y=100)
                noise_val = (noise_val + 1) / 2
                if noise_val < biome_config['gap_probability']:
                    # Variable gap width 2-4 tiles
                    gap_width = 2 + int(abs(self.obstacle_noise.noise2(x=global_x * 0.25, y=200)) * 2.5)
                    gap_width = min(gap_width, PLAYER_MAX_JUMP_DISTANCE)  # Cap at max jumpable

                    if x + gap_width < width:
                        height_before = heights[x - 1] if x > 0 else heights[x]
                        height_after = heights[min(x + gap_width, width - 1)]
                        height_diff = abs(height_before - height_after)

                        # Only reject if clearly impossible
                        if gap_width <= PLAYER_MAX_JUMP_DISTANCE and height_diff <= PLAYER_MAX_JUMP_HEIGHT:
                            gaps.append((x, gap_width))
                            last_gap_end = x + gap_width
                            x += gap_width
                            continue
            x += 1
        return gaps

    def generate_floating_platforms(self, heights, width, height, offset, biome_config):
        platforms = []
        min_gap_for_platform = 2  # Place platforms over gaps of 2+ tiles

        # First pass: identify where platforms would help bridge gaps
        gap_positions = set()
        for x in range(width):
            terrain_height = heights[x]
            # Check if this is a "missing" spot that needs a platform
            if terrain_height == 0 or (x > 0 and abs(heights[x] - heights[x - 1]) > 2):
                gap_positions.add(x)

        # Second pass: place platforms strategically
        x = 0
        while x < width:
            global_x = x + offset * width
            noise_val = self.obstacle_noise.noise2(x=global_x * 0.2, y=500)
            noise_val = (noise_val + 1) / 2

            should_place = noise_val < biome_config['platform_probability']
            # Boost probability over gaps
            if x in gap_positions:
                should_place = should_place or (noise_val < biome_config['platform_probability'] * 1.5)

            if should_place:
                base_height = heights[x] if heights[x] > 0 else 3

                # Variable platform height (3-6 tiles above terrain)
                height_noise = abs(self.terrain_noise.noise2(x=global_x * 0.15, y=600))
                height_above = MIN_PLATFORM_HEIGHT_ABOVE + int(
                    height_noise * (MAX_PLATFORM_HEIGHT_ABOVE - MIN_PLATFORM_HEIGHT_ABOVE))

                # Variable platform width (2-5 tiles)
                width_noise = abs(self.terrain_noise.noise2(x=global_x * 0.25, y=700))
                plat_width = 2 + int(width_noise * 3)

                platform_y = base_height + height_above

                # More lenient bounds checking
                if platform_y < height - 2 and x + plat_width <= width:
                    platforms.append({
                        'x': x,
                        'y': platform_y,
                        'width': plat_width,
                        'type': 'static'
                    })
                    x += plat_width
                    continue
            x += 1

        return platforms

    def generate_obstacles(self, heights, width, offset, biome_config):
        obstacles = []
        for x in range(width):
            global_x = x + offset * width
            noise_val = self.obstacle_noise.noise2(x=global_x * 0.4, y=800)
            noise_val = (noise_val + 1) / 2
            if noise_val < biome_config['obstacle_probability']:
                terrain_height = heights[x]
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

    def generate_cave_ceiling(self, width, offset):
        ceiling = []
        for x in range(width):
            global_x = x + offset * width
            noise_val = self.terrain_noise.noise2(x=global_x * 0.12, y=1000)
            noise_val = (noise_val + 1) / 2
            ceiling_height = 2 + int(noise_val * 3)
            ceiling.append(ceiling_height)
        return ceiling

    def generate_chunk(self, width=20, height=15, offset=0):
        chunk = [[0 for _ in range(width)] for _ in range(height)]
        chunk_centre_x = offset * width + width // 2
        biome = self.determine_biome(chunk_centre_x)
        biome_config = self.get_biome_config(biome)
        heights = self.generate_terrain_heights(width, offset, biome_config)

        for x in range(width):
            terrain_height = heights[x]
            for y in range(height - 1, height - terrain_height - 1, -1):
                if 0 <= y < height:
                    chunk[y][x] = 1

        gaps = self.generate_gaps(heights, width, offset, biome_config)
        for gap_x, gap_width in gaps:
            for x in range(gap_x, min(gap_x + gap_width, width)):
                for y in range(height):
                    chunk[y][x] = 0

        platforms = self.generate_floating_platforms(heights, width, height, offset, biome_config)
        for platform in platforms:
            plat_y = height - 1 - platform['y']
            if 0 <= plat_y < height:
                for dx in range(platform['width']):
                    if platform['x'] + dx < width:
                        chunk[plat_y][platform['x'] + dx] = 1

        obstacles = self.generate_obstacles(heights, width, offset, biome_config)
        for obstacle in obstacles:
            obs_y = height - 1 - obstacle['y'] - 1
            if not (0 <= obs_y < height and obstacle['x'] < width):
                continue
            if chunk[obs_y + 1][obstacle['x']] != 1 and obstacle['type'] == ObstacleType.SPIKE:
                continue
            chunk[obs_y][obstacle['x']] = obstacle['type']

        if biome == BiomeType.CAVES:
            ceiling_heights = self.generate_cave_ceiling(width, offset)
            for x in range(width):
                for y in range(ceiling_heights[x]):
                    chunk[y][x] = 1

        return chunk

    def generate_valid_chunk(self, width=20, height=15, offset=0, max_attempts=10):
        """Generate and validate chunk, with fallback to flat chunk"""
        if offset == 0:
            return self.generate_flat_chunk(width, height, offset, self.seed)

        for attempt in range(max_attempts):
            chunk = self.generate_chunk(width, height, offset)
            is_valid, reachable = self.validate_chunk_traversable(chunk, width, height)

            if is_valid:
                print(f"Chunk {offset} valid on attempt {attempt + 1}/{max_attempts}")
                return chunk

            print(f" Chunk {offset} attempt {attempt + 1}/{max_attempts} failed ({len(reachable)} positions)")

            # Vary generation strategy based on attempt
            if attempt < 3:
                # First few attempts: reduce gaps slightly
                self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 137)
            elif attempt < 6:
                # Middle attempts: adjust terrain
                self.terrain_noise = OpenSimplex(self.seed + attempt * 73)
                self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 137)
            else:
                # Later attempts: more drastic changes
                self.terrain_noise = OpenSimplex(self.seed + attempt * 211)
                self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 317)
                self.biome_noise = OpenSimplex(self.seed + 1000 + attempt * 113)

        print(f"Chunk {offset} failed after {max_attempts} attempts - using flat chunk")
        return self.generate_flat_chunk(width, height, offset, self.seed)

    def validate_chunk_traversable(self, chunk, width, height):
        """BFS pathfinding with proper termination conditions"""
        MAX_NODES = 2500  # Increased for complex chunks
        TIMEOUT_SECONDS = 2.0  # Increased timeout for complex validation

        def get_ground_level(x):
            for y in range(height - 1, -1, -1):
                if chunk[y][x] == 1:
                    return y - 1
            return None

        def is_solid(x, y):
            if not (0 <= x < width and 0 <= y < height):
                return False
            return chunk[y][x] == 1

        def is_valid_position(x, y):
            if not (0 <= x < width and 0 <= y < height):
                return False
            if is_solid(x, y):
                return False
            # Spikes are deadly - can't occupy same space
            if chunk[y][x] == ObstacleType.SPIKE:
                return False
            return True

        def simulate_jump(start_x, start_y, direction):
            path = []
            for distance in range(1, PLAYER_MAX_JUMP_DISTANCE + 1):
                x = start_x + (distance * direction)
                if not (0 <= x < width):
                    break

                progress = distance / PLAYER_MAX_JUMP_DISTANCE
                height_offset = int(PLAYER_MAX_JUMP_HEIGHT * (4 * progress * (1 - progress)))
                y = start_y - height_offset

                if not is_valid_position(x, y):
                    break
                path.append((x, y))

            if not path:
                return None

            last_x, last_y = path[-1]
            land_y = last_y

            while land_y < height - 1 and not is_solid(last_x, land_y + 1):
                land_y += 1
                if not is_valid_position(last_x, land_y):
                    return None

            if land_y >= height:
                return None

            return (last_x, land_y)

        def get_neighbors(x, y):
            neighbors = []
            on_ground = is_solid(x, y + 1)

            if not on_ground:
                return []

            # Check if standing on a spike (deadly position)
            if y + 1 < height and chunk[y + 1][x] == ObstacleType.SPIKE:
                return []  # Can't stand on spikes

            # Walk right
            if x < width - 1:
                next_x = x + 1
                # Check if we can walk to next position
                if is_valid_position(next_x, y):
                    if is_solid(next_x, y + 1):
                        # Ground continues - but check for spike on top
                        if y < height and chunk[y][next_x] != ObstacleType.SPIKE:
                            neighbors.append((next_x, y))
                    else:
                        # Walk off edge - fall straight down
                        fall_y = y
                        while fall_y < height - 1 and not is_solid(next_x, fall_y + 1):
                            fall_y += 1
                        if fall_y < height and is_valid_position(next_x, fall_y):
                            # Check landing spot doesn't have spike
                            if chunk[fall_y][next_x] != ObstacleType.SPIKE:
                                neighbors.append((next_x, fall_y))

            # Try jumps of different distances
            for jump_dist in [PLAYER_MAX_JUMP_DISTANCE, PLAYER_MAX_JUMP_DISTANCE - 1, PLAYER_MAX_JUMP_DISTANCE - 2]:
                if jump_dist < 1:
                    continue
                jump_landing = simulate_jump(x, y, direction=1)
                if jump_landing:
                    land_x, land_y = jump_landing
                    # Verify landing spot is safe (no spike)
                    if land_y < height and chunk[land_y][land_x] != ObstacleType.SPIKE:
                        if jump_landing not in neighbors:
                            neighbors.append(jump_landing)

            return neighbors

        # Find starting position
        start_x = 0
        start_y = get_ground_level(start_x)

        if start_y is None or start_y < 0:
            return False, set()

        # BFS with timeout and node limit
        start_time = time.time()
        queue = deque([(start_x, start_y)])
        visited = {(start_x, start_y)}
        max_x_reached = start_x

        while queue:
            # Safety checks
            if time.time() - start_time > TIMEOUT_SECONDS:
                print(f"Timeout (reached x={max_x_reached}/{width - 1})")
                return False, visited

            if len(visited) > MAX_NODES:
                print(f"  Node limit (reached x={max_x_reached}/{width - 1})")
                return False, visited

            x, y = queue.popleft()
            max_x_reached = max(max_x_reached, x)

            # Success condition
            if x >= width - 1:
                return True, visited

            # Explore neighbors
            for next_x, next_y in get_neighbors(x, y):
                if (next_x, next_y) not in visited:
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))

        # Checked all reachable positions without reaching end
        print(f" Dead end at x={max_x_reached}/{width - 1}")
        return False, visited
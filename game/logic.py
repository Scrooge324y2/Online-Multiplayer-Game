from opensimplex import OpenSimplex
import random
from collections import deque
import time

TILE_SIZE = 1 # Number of array units per tile, can be used for scaling if needed
BIOME_CHUNK_LENGTH = 5  # how many chunks each biome lasts
PLAYER_MAX_JUMP_HEIGHT = 3
PLAYER_MAX_JUMP_DISTANCE = 4
MAX_PLATFORM_HEIGHT_ABOVE = 6
MIN_PLATFORM_HEIGHT_ABOVE = 3
MAX_PIT_DEPTH = PLAYER_MAX_JUMP_HEIGHT
MIN_SPIKE_GAP = 4


class Biome:
    def get_config(self, difficulty):
        raise NotImplementedError


class Plain(Biome):
    def get_config(self, difficulty):
        return {
            'height_multiplier': 5,
            'gap_probability': min(0.5, 0.2 * (0.5 + difficulty * 0.5)),
            'spike_probability': min(0.8, 0.4 * difficulty),
            'platform_probability': 0.35 / (0.8 + difficulty * 0.2),
        }


class Hill(Biome):
    def get_config(self, difficulty):
        return {
            'height_multiplier': 7,
            'gap_probability': min(0.5, 0.25 * (0.5 + difficulty * 0.5)),
            'spike_probability': min(0.8, 0.5 * difficulty),
            'platform_probability': 0.4 / (0.8 + difficulty * 0.2),
        }


class Mountain(Biome):
    def get_config(self, difficulty):
        return {
            'height_multiplier': 9,
            'gap_probability': min(0.5, 0.3 * (0.5 + difficulty * 0.5)),
            'spike_probability': min(0.8, 0.6 * difficulty),
            'platform_probability': 0.5 / (0.8 + difficulty * 0.2),
        }


class Cave(Biome):
    def get_config(self, difficulty):
        return {
            'height_multiplier': 6,
            'has_ceiling': True,
            'gap_probability': min(0.5, 0.15 * (0.5 + difficulty * 0.5)),
            'spike_probability': min(0.8, 0.45 * difficulty),
            'platform_probability': 0.6 / (0.8 + difficulty * 0.2),
        }



class ObstacleType:
    SPIKE = 2
    CEILING = 3



class ProceduralGenerator:
    def __init__(self, seed):
        """
        Sets up multiple OpenSimplex noise generators for terrain,
        biome selection, and obstacle placement. Also initialises
        difficulty scaling and a seeded random generator to ensure
        consistent generation across clients.
        """
        self.seed = seed
        self.difficulty = 0.5 #goes from 0.5 o 2.0
        self.terrain_noise = OpenSimplex(seed)
        self.biome_noise = OpenSimplex(seed + 1000)
        self.obstacle_noise = OpenSimplex(seed + 2000)
        self.rng = random.Random(seed)

    def increase_difficulty(self, percent_increase):
        """Gradually increases difficulty up to a maximum of 2.0,
        affecting terrain features such as gap size, spike frequency,
        and platform placement."""
        if self.difficulty != 2.0:
            self.difficulty = min(2.0, self.difficulty + 0.02 * percent_increase)

    def generate_flat_chunk(self, width=20, height=15):
        chunk = [[0 for x in range(width)] for y in range(height)]
        terrain_height = 1
        for x in range(width):
            for y in range(height - 1, height - terrain_height - 1, -1):
                chunk[y][x] = 1
        return chunk

    def is_jump_possible(self, from_y, to_y, dx):
        """Determines if a jump is possible based on horizontal distance and vertical height difference."""
        dy = to_y - from_y
        if dx > PLAYER_MAX_JUMP_DISTANCE:
            return False
        if dy > PLAYER_MAX_JUMP_HEIGHT:
            return False
        return True

    def determine_biome(self, global_x):
        chunk = global_x // (20 * BIOME_CHUNK_LENGTH)

        # Use chunk index as seed so each chunk always gets the same biome
        rng = random.Random(self.seed + chunk * 999)
        biomes = [Plain(), Hill(), Mountain(), Cave()]

        # Keep trying until there is a different biome from the previous chunk
        biome = rng.choice(biomes)
        if chunk > 0:
            prev_rng = random.Random(self.seed + (chunk - 1) * 999)
            prev_biome = prev_rng.choice(biomes)
            while type(biome) == type(prev_biome):
                biome = rng.choice(biomes)

        return biome



    def generate_terrain_heights(self, width, offset, biome_config):
        """
        Combines multiple noise layers (base + detail) to produce
        varied terrain, scaled by biome difficulty.
        """
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
        # Difficulty affects spacing - harder = less spacing between gaps
        min_spacing = max(3, int(5 - self.difficulty))  # 4-5 tiles at easy, 3 tiles at hard
        last_gap_end = -min_spacing
        x = 0
        while x < width:
            global_x = x + offset * width
            if x - last_gap_end >= min_spacing:
                noise_val = self.obstacle_noise.noise2(x=global_x * 0.3, y=100)
                noise_val = (noise_val + 1) / 2
                if noise_val < biome_config['gap_probability']:
                    # Difficulty affects gap width - harder = potentially bigger gaps
                    base_width = 2 + int(abs(self.obstacle_noise.noise2(x=global_x * 0.25, y=200)) * 2.5)
                    # Scale gap width with difficulty (but keep it jumpable)
                    gap_width = min(PLAYER_MAX_JUMP_DISTANCE, int(base_width * (0.8 + self.difficulty * 0.2)))

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
        """
        Uses a two-pass system:
        1. Identifies gaps or difficult terrain sections.
        2. Places platforms probabilistically, with increased likelihood
           over problematic areas to maintain playability.
        """
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

                right_col = x + plat_width

                if right_col < width:
                    if heights[right_col] >= platform_y + 1:
                        x += 1
                        continue

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
        """
        Generate a chunk of terrain with the given width and height, influenced by the biome type determined from the offset.
        """
        chunk = [[0 for _ in range(width)] for _ in range(height)]
        chunk_centre_x = offset * width + width // 2
        biome = self.determine_biome(chunk_centre_x)
        biome_config = biome.get_config(self.difficulty)
        heights = self.generate_terrain_heights(width, offset, biome_config)

        for x in range(width): # Draw terrain
            terrain_height = heights[x]
            for y in range(height - 1, height - terrain_height - 1, -1):
                if 0 <= y < height:
                    chunk[y][x] = 1

        gaps = self.generate_gaps(heights, width, offset, biome_config)#add gaps
        for gap_x, gap_width in gaps:
            for x in range(gap_x, min(gap_x + gap_width, width)):
                surface_y = None
                for y in range(height):
                    if chunk[y][x] == 1:
                        surface_y = y
                        break

                if surface_y is None:
                    continue

                pit_bottom = min(height - 1, surface_y + MAX_PIT_DEPTH)

                for y in range(surface_y, pit_bottom):
                    chunk[y][x] = 0

        platforms = self.generate_floating_platforms(heights, width, height, offset, biome_config) #add floating platforms
        for platform in platforms:
            plat_y = height - 1 - platform['y']
            if 0 <= plat_y < height:
                for dx in range(platform['width']):
                    if platform['x'] + dx < width:
                        chunk[plat_y][platform['x'] + dx] = 1

        if isinstance(biome, Cave):
            ceiling_heights = self.generate_cave_ceiling(width, offset)
            for x in range(width):
                for y in range(ceiling_heights[x]):
                    chunk[y][x] = ObstacleType.CEILING


        return chunk, biome

    def count_obstacles(self, chunk):
        counts = {2: 0, 3: 0}

        for row in chunk:
            for tile in row:
                if tile in counts:
                    counts[tile] += 1

        return counts

    def place_spikes_from_visited(self, chunk, visited, biome_config, offset):
        self.rng.seed(self.seed + offset * 8000)
        positions = sorted(visited, key=lambda p: p[0])

        last_spike_x = -999
        min_gap = max(MIN_SPIKE_GAP, int(4 / self.difficulty))  # base gap = 4 at difficulty 1

        for x, y in positions:
            # Skip edges
            if x < 2 or x > len(chunk[0]) - 3:
                continue

            # Enforce horizontal spacing
            if x - last_spike_x < min_gap:
                continue

            if self.rng.random() > biome_config['spike_probability']:
                continue

            # Place spike in air above ground
            if chunk[y][x] != 0:
                continue

            if y + 1 >= len(chunk) or chunk[y + 1][x] != 1:
                continue

            chunk[y][x] = ObstacleType.SPIKE
            last_spike_x = x

        return chunk

    def generate_valid_chunk(self, width=20, height=15, offset=0, max_attempts=10, attempt=0, prev_chunk=None):
        """
         Uses recursive retry logic:
        - Generates a chunk
        - Validates it using BFS traversal
        - If invalid, modifies noise seeds and retries

        Falls back to a flat chunk if maximum attempts are exceeded."""
        if offset == 0:
            return self.generate_flat_chunk(width, height), "Plain"

        # Save original noise only at the top-level call so retries can
        # mutate freely, but future chunks are never affected.
        if attempt == 0:
            saved_terrain_noise = self.terrain_noise
            saved_obstacle_noise = self.obstacle_noise
            saved_biome_noise = self.biome_noise
        else:
            saved_terrain_noise = None
            saved_obstacle_noise = None
            saved_biome_noise = None

        def restore_noise():
            if saved_terrain_noise is not None:
                self.terrain_noise = saved_terrain_noise
                self.obstacle_noise = saved_obstacle_noise
                self.biome_noise = saved_biome_noise


        # Base case - max attempts reached, fall back to flat chunk
        if attempt >= max_attempts:
            return self.generate_flat_chunk(width, height), "Plain"

        # Vary noise based on attempt number
        if attempt < 3:
            self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 137)
        elif attempt < 6:
            self.terrain_noise = OpenSimplex(self.seed + attempt * 73)
            self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 137)
        else:
            self.terrain_noise = OpenSimplex(self.seed + attempt * 211)
            self.obstacle_noise = OpenSimplex(self.seed + 2000 + attempt * 317)
            self.biome_noise = OpenSimplex(self.seed + 1000 + attempt * 113)

        chunk, biome = self.generate_chunk(width, height, offset)
        is_valid, reachable = self.validate_chunk_traversable(chunk, width, height, prev_chunk)

        if is_valid:
            biome_config = biome.get_config(self.difficulty)
            restore_noise()  # restore so future chunks use clean generator
            return self.place_spikes_from_visited(chunk, reachable, biome_config, offset), type(biome).__name__ # returns the chunk with spikes placed, and the biome name for client to use in rendering

        # Recursive case - try again with next attempt
        return self.generate_valid_chunk(width, height, offset, max_attempts, attempt + 1, prev_chunk)

    def validate_chunk_traversable(self, chunk, width, height, prev_chunk=None):
        """
         Simulates player movement including walking, falling,
        and jumping. Uses breadth-first search to explore all
        reachable states while enforcing constraints such as:
        - Maximum jump height and distance
        - Terrain collisions
        - Boundary continuity with previous chunk

        Includes safety limits (node count and timeout) to
        prevent excessive computation.

        """
        MAX_NODES = 2500
        TIMEOUT_SECONDS = 2.0

        def get_ground_level(x):
            for y in range(height - 1, -1, -1):
                if chunk[y][x] == 1:
                    return y - 1
            return None

        def is_solid(x, y):
            if not (0 <= x < width and 0 <= y < height):
                return False
            return chunk[y][x] in (1, ObstacleType.CEILING)

        def is_valid_position(x, y):
            if not (0 <= x < width and 0 <= y < height):
                return False
            if is_solid(x, y):
                return False

            return True

        def simulate_jump(start_x, start_y, jump_dist, direction):
            path = []
            for distance in range(1, jump_dist + 1):
                x = start_x + (distance * direction)
                if not (0 <= x < width):
                    break

                progress = distance / jump_dist
                height_offset = int(PLAYER_MAX_JUMP_HEIGHT * (4 * progress * (1 - progress)))
                y = start_y - height_offset

                if not is_valid_position(x, y):
                    break
                path.append((x, y))

            if not path:
                return None

            last_x, last_y = path[-1]
            land_y = last_y

            # Fall until hitting solid ground
            while land_y < height - 1:
                below_solid = is_solid(last_x, land_y + 1)
                if below_solid:
                    break
                land_y += 1
                if not is_valid_position(last_x, land_y):
                    return None

            if land_y >= height:
                return None

            return (last_x, land_y)

        def get_neighbours(x, y):
            neighbours = []
            on_ground = is_solid(x, y + 1)


            if not on_ground:
                return []


            # Walk right
            if x < width - 1:
                next_x = x + 1
                # Check if we can walk to next position
                if is_valid_position(next_x, y):
                    next_ground = is_solid(next_x, y + 1)

                    if next_ground :
                        neighbours.append((next_x, y))
                    else:
                        # Walk off edge - fall straight down
                        fall_y = y
                        while fall_y < height - 1:
                            below_solid = is_solid(next_x, fall_y + 1)
                            if below_solid:
                                break
                            fall_y += 1

                        if fall_y < height and is_valid_position(next_x, fall_y):
                            neighbours.append((next_x, fall_y))

            # Try jumps of different distances
            for jump_dist in [PLAYER_MAX_JUMP_DISTANCE, PLAYER_MAX_JUMP_DISTANCE - 1, PLAYER_MAX_JUMP_DISTANCE - 2]:
                if jump_dist < 1:
                    continue
                jump_landing = simulate_jump(x, y, jump_dist, direction=1)
                if jump_landing:
                    land_x, land_y = jump_landing
                    if land_y < height:
                        if jump_landing not in neighbours:
                            neighbours.append(jump_landing)

            return neighbours

        def validate_chunk_boundary(prev_chunk, chunk, height):
            height_count1 = 0
            height_count2 = 0

            for y in range(height-1, -1, -1):
                if prev_chunk[y][len(prev_chunk[0]) - 1] == 1:
                    height_count1 += 1
                else:
                    break

            for y in range(height-1, -1, -1):
                if chunk[y][0] == 1:
                    height_count2 += 1
                else:
                    break

            return (height_count2 - height_count1) <= PLAYER_MAX_JUMP_HEIGHT


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
                return False, visited

            if len(visited) > MAX_NODES:
                return False, visited

            x, y = queue.popleft()
            max_x_reached = max(max_x_reached, x)

            # Success condition
            if x >= width - 1:
                if prev_chunk is not None:
                    if not validate_chunk_boundary(prev_chunk, chunk, height):
                        return False, visited
                return True, visited

            # Explore neighbours
            for next_x, next_y in get_neighbours(x, y):
                if (next_x, next_y) not in visited:
                    visited.add((next_x, next_y))
                    queue.append((next_x, next_y))

        return False, visited # returns a set of all reachable positions
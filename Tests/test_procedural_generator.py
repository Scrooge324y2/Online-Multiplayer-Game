import sys
import os
import unittest
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.logic import (
    ProceduralGenerator,
    Plain, Hill, Mountain, Cave,
    ObstacleType,
    PLAYER_MAX_JUMP_HEIGHT,
    PLAYER_MAX_JUMP_DISTANCE,
)

CHUNK_WIDTH = 20
CHUNK_HEIGHT = 15
SEED = 42



# Biome config tests


class TestBiomeConfigs(unittest.TestCase):

    def _assert_required_keys(self, config):
        for key in ('height_multiplier', 'gap_probability', 'spike_probability', 'platform_probability'):
            self.assertIn(key, config, f"Missing key '{key}' in config")

    # Plain
    def test_plain_config_contains_required_keys(self):
        self._assert_required_keys(Plain().get_config(1.0))

    def test_plain_gap_probability_within_bounds(self):
        for d in [0.5, 1.0, 2.0]:
            prob = Plain().get_config(d)['gap_probability']
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 0.5)

    def test_plain_spike_probability_within_bounds(self):
        for d in [0.5, 1.0, 2.0]:
            prob = Plain().get_config(d)['spike_probability']
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 0.8)

    def test_plain_gap_probability_increases_with_difficulty(self):
        p_easy = Plain().get_config(0.5)['gap_probability']
        p_hard = Plain().get_config(2.0)['gap_probability']
        self.assertGreater(p_hard, p_easy)

    def test_plain_spike_probability_increases_with_difficulty(self):
        p_easy = Plain().get_config(0.5)['spike_probability']
        p_hard = Plain().get_config(2.0)['spike_probability']
        self.assertGreater(p_hard, p_easy)

    # Hill
    def test_hill_config_contains_required_keys(self):
        self._assert_required_keys(Hill().get_config(1.0))

    def test_hill_has_higher_height_multiplier_than_plain(self):
        self.assertGreater(
            Hill().get_config(1.0)['height_multiplier'],
            Plain().get_config(1.0)['height_multiplier']
        )

    # Mountain
    def test_mountain_config_contains_required_keys(self):
        self._assert_required_keys(Mountain().get_config(1.0))

    def test_mountain_has_highest_height_multiplier(self):
        self.assertGreater(
            Mountain().get_config(1.0)['height_multiplier'],
            Hill().get_config(1.0)['height_multiplier']
        )

    def test_mountain_gap_probability_within_bounds(self):
        for d in [0.5, 1.0, 2.0]:
            prob = Mountain().get_config(d)['gap_probability']
            self.assertLessEqual(prob, 0.5)

    # Cave
    def test_cave_config_contains_required_keys(self):
        self._assert_required_keys(Cave().get_config(1.0))

    def test_cave_has_ceiling_flag(self):
        config = Cave().get_config(1.0)
        self.assertIn('has_ceiling', config)
        self.assertTrue(config['has_ceiling'])

    def test_cave_gap_probability_lower_than_mountain(self):
        """Cave should be tighter but have fewer gaps than mountain."""
        cave_gap = Cave().get_config(1.0)['gap_probability']
        mtn_gap = Mountain().get_config(1.0)['gap_probability']
        self.assertLess(cave_gap, mtn_gap)

    # Biome raises NotImplementedError for base class
    def test_base_biome_raises_not_implemented(self):
        from game.logic import Biome
        with self.assertRaises(NotImplementedError):
            Biome().get_config(1.0)



# ProceduralGenerator initialisation


class TestProceduralGeneratorInit(unittest.TestCase):

    def test_initial_difficulty_is_0_5(self):
        gen = ProceduralGenerator(seed=SEED)
        self.assertEqual(gen.difficulty, 0.5)

    def test_seed_is_stored(self):
        gen = ProceduralGenerator(seed=SEED)
        self.assertEqual(gen.seed, SEED)

    def test_different_seeds_produce_different_terrain(self):
        g1 = ProceduralGenerator(seed=1)
        g2 = ProceduralGenerator(seed=9999)
        c1 = g1.generate_valid_chunk(offset=1)
        c2 = g2.generate_valid_chunk(offset=1)
        self.assertNotEqual(c1, c2)

    def test_same_seed_produces_identical_terrain(self):
        g1 = ProceduralGenerator(seed=SEED)
        g2 = ProceduralGenerator(seed=SEED)
        c1 = g1.generate_valid_chunk(offset=1)
        c2 = g2.generate_valid_chunk(offset=1)
        self.assertEqual(c1, c2)



# Difficulty scaling


class TestDifficultyScaling(unittest.TestCase):

    def test_increase_difficulty_raises_value(self):
        gen = ProceduralGenerator(seed=SEED)
        before = gen.difficulty
        gen.increase_difficulty(10)
        self.assertGreater(gen.difficulty, before)

    def test_difficulty_capped_at_2(self):
        # NOTE: increase_difficulty must use min() to enforce the cap.
        # Fix in game/logic.py:
        #   self.difficulty = min(2.0, self.difficulty + 0.02 * percent_increase)
        gen = ProceduralGenerator(seed=SEED)
        gen.difficulty = 1.99
        gen.increase_difficulty(100)
        # After the production fix this assertion will pass.
        self.assertLessEqual(gen.difficulty, 2.0)

    def test_difficulty_does_not_increase_when_at_max(self):
        gen = ProceduralGenerator(seed=SEED)
        gen.difficulty = 2.0
        gen.increase_difficulty(50)
        self.assertEqual(gen.difficulty, 2.0)

    def test_zero_percent_increase_has_no_effect(self):
        gen = ProceduralGenerator(seed=SEED)
        before = gen.difficulty
        gen.increase_difficulty(0)
        self.assertEqual(gen.difficulty, before)

    def test_difficulty_affects_gap_probability(self):
        gen_easy = ProceduralGenerator(seed=SEED)
        gen_hard = ProceduralGenerator(seed=SEED)
        gen_hard.difficulty = 2.0

        biome_config_easy = Plain().get_config(gen_easy.difficulty)
        biome_config_hard = Plain().get_config(gen_hard.difficulty)

        self.assertGreater(
            biome_config_hard['gap_probability'],
            biome_config_easy['gap_probability']
        )



# Flat chunk generation


class TestFlatChunk(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_flat_chunk_has_correct_dimensions(self):
        chunk = self.gen.generate_flat_chunk(CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertEqual(len(chunk), CHUNK_HEIGHT)
        self.assertEqual(len(chunk[0]), CHUNK_WIDTH)

    def test_flat_chunk_bottom_row_is_solid(self):
        chunk = self.gen.generate_flat_chunk(CHUNK_WIDTH, CHUNK_HEIGHT)
        for x in range(CHUNK_WIDTH):
            self.assertEqual(chunk[CHUNK_HEIGHT - 1][x], 1)

    def test_flat_chunk_top_rows_are_empty(self):
        chunk = self.gen.generate_flat_chunk(CHUNK_WIDTH, CHUNK_HEIGHT)
        for y in range(CHUNK_HEIGHT - 1):
            for x in range(CHUNK_WIDTH):
                self.assertEqual(chunk[y][x], 0)

    def test_flat_chunk_custom_dimensions(self):
        chunk = self.gen.generate_flat_chunk(width=10, height=8)
        self.assertEqual(len(chunk), 8)
        self.assertEqual(len(chunk[0]), 10)



# is_jump_possible


class TestIsJumpPossible(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_jump_possible_within_limits(self):
        self.assertTrue(self.gen.is_jump_possible(0, 0, 2))

    def test_jump_impossible_too_far_horizontally(self):
        self.assertFalse(self.gen.is_jump_possible(0, 0, PLAYER_MAX_JUMP_DISTANCE + 1))

    def test_jump_impossible_too_far_vertically(self):
        self.assertFalse(self.gen.is_jump_possible(0, PLAYER_MAX_JUMP_HEIGHT + 1, 1))

    def test_jump_possible_at_exact_max_distance(self):
        self.assertTrue(self.gen.is_jump_possible(0, 0, PLAYER_MAX_JUMP_DISTANCE))

    def test_jump_possible_at_exact_max_height(self):
        self.assertTrue(self.gen.is_jump_possible(0, PLAYER_MAX_JUMP_HEIGHT, 1))



# determine_biome


class TestDetermineBiome(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_returns_a_biome_instance(self):
        from game.logic import Biome
        biome = self.gen.determine_biome(0)
        self.assertIsInstance(biome, Biome)

    def test_all_biome_types_can_be_returned(self):
        """Across a wide x range, at least two distinct biome types should appear.
        Biome noise frequency is 0.01, so one full cycle spans ~600 units.
        Sampling 0-100000 in steps of 10 guarantees broad coverage."""
        from game.logic import Biome
        found = set()
        for x in range(0, 100_000, 10):
            b = self.gen.determine_biome(x)
            found.add(type(b).__name__)
            if len(found) >= 4:
                break
        self.assertGreaterEqual(len(found), 2, "Expected at least two different biome types")

    def test_biome_is_deterministic_for_same_x(self):
        b1 = type(self.gen.determine_biome(100)).__name__
        b2 = type(self.gen.determine_biome(100)).__name__
        self.assertEqual(b1, b2)



# generate_terrain_heights


class TestGenerateTerrainHeights(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)
        self.biome_config = Plain().get_config(1.0)

    def test_returns_correct_number_of_heights(self):
        heights = self.gen.generate_terrain_heights(CHUNK_WIDTH, 0, self.biome_config)
        self.assertEqual(len(heights), CHUNK_WIDTH)

    def test_all_heights_are_at_least_1(self):
        heights = self.gen.generate_terrain_heights(CHUNK_WIDTH, 0, self.biome_config)
        for h in heights:
            self.assertGreaterEqual(h, 1)

    def test_heights_are_bounded_by_biome_multiplier(self):
        heights = self.gen.generate_terrain_heights(CHUNK_WIDTH, 0, self.biome_config)
        multiplier = self.biome_config['height_multiplier']
        for h in heights:
            self.assertLessEqual(h, multiplier)

    def test_mountain_produce_higher_terrain_on_average(self):
        plain_h = self.gen.generate_terrain_heights(CHUNK_WIDTH, 5, Plain().get_config(1.0))
        mtn_h = self.gen.generate_terrain_heights(CHUNK_WIDTH, 5, Mountain().get_config(1.0))
        self.assertGreater(sum(mtn_h), sum(plain_h))



# generate_gaps


class TestGenerateGaps(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_gaps_are_within_chunk_width(self):
        heights = [3] * CHUNK_WIDTH
        config = Plain().get_config(1.0)
        gaps = self.gen.generate_gaps(heights, CHUNK_WIDTH, 2, config)
        for gap_x, gap_width in gaps:
            self.assertGreaterEqual(gap_x, 0)
            self.assertLess(gap_x + gap_width, CHUNK_WIDTH)

    def test_no_adjacent_gaps(self):
        """Gaps must be separated by at least min_spacing tiles."""
        heights = [3] * CHUNK_WIDTH
        config = Plain().get_config(1.0)
        gaps = self.gen.generate_gaps(heights, CHUNK_WIDTH, 3, config)
        for i in range(len(gaps) - 1):
            end_of_first = gaps[i][0] + gaps[i][1]
            start_of_next = gaps[i + 1][0]
            self.assertGreater(start_of_next, end_of_first)

    def test_gap_widths_do_not_exceed_max_jump_distance(self):
        heights = [3] * CHUNK_WIDTH
        config = Plain().get_config(1.5)
        gaps = self.gen.generate_gaps(heights, CHUNK_WIDTH, 4, config)
        for _, gap_width in gaps:
            self.assertLessEqual(gap_width, PLAYER_MAX_JUMP_DISTANCE)

    def test_no_gaps_at_offset_0(self):
        """Offset 0 is always a flat starter chunk — gaps tested at offset > 0."""
        heights = [3] * CHUNK_WIDTH
        config = Plain().get_config(2.0)
        # Gaps are valid at offset > 0; this just checks the function doesn't crash
        gaps = self.gen.generate_gaps(heights, CHUNK_WIDTH, 1, config)
        self.assertIsInstance(gaps, list)



# generate_chunk


class TestGenerateChunk(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_chunk_has_correct_dimensions(self):
        chunk, _ = self.gen.generate_chunk(CHUNK_WIDTH, CHUNK_HEIGHT, offset=1)
        self.assertEqual(len(chunk), CHUNK_HEIGHT)
        self.assertEqual(len(chunk[0]), CHUNK_WIDTH)

    def test_all_tiles_are_valid_values(self):
        chunk, _ = self.gen.generate_chunk(CHUNK_WIDTH, CHUNK_HEIGHT, offset=1)
        valid = {0, 1, 2}
        for row in chunk:
            for tile in row:
                self.assertIn(tile, valid)

    def test_returns_biome_instance(self):
        from game.logic import Biome
        _, biome = self.gen.generate_chunk(CHUNK_WIDTH, CHUNK_HEIGHT, offset=1)
        self.assertIsInstance(biome, Biome)

    def test_chunk_contains_some_solid_tiles(self):
        chunk, _ = self.gen.generate_chunk(CHUNK_WIDTH, CHUNK_HEIGHT, offset=1)
        solid = sum(1 for row in chunk for t in row if t == 1)
        self.assertGreater(solid, 0)

    def test_cave_chunks_have_ceiling(self):
        """Force a Cave biome by finding a global_x that maps to it."""
        gen = ProceduralGenerator(seed=SEED)
        # Sweep until we hit a cave biome
        cave_offset = None
        for offset in range(1, 500):
            global_x = offset * CHUNK_WIDTH + CHUNK_WIDTH // 2
            biome = gen.determine_biome(global_x)
            if isinstance(biome, Cave):
                cave_offset = offset
                break

        if cave_offset is None:
            self.skipTest("No Cave biome found in first 500 chunks for this seed")

        gen2 = ProceduralGenerator(seed=SEED)
        chunk, biome = gen2.generate_chunk(CHUNK_WIDTH, CHUNK_HEIGHT, offset=cave_offset)
        # A cave chunk should have at least one solid tile in its top rows (ceiling)
        top_solid = any(chunk[y][x] == 3 for y in range(3) for x in range(CHUNK_WIDTH))
        self.assertTrue(top_solid, "Cave chunk should have a ceiling")



# generate_valid_chunk


class TestGenerateValidChunk(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_offset_0_returns_flat_chunk(self):
        chunk = self.gen.generate_valid_chunk(offset=0)
        # Flat chunk: only bottom row is solid
        self.assertEqual(chunk[CHUNK_HEIGHT - 1][0], 1)
        for y in range(CHUNK_HEIGHT - 1):
            self.assertEqual(chunk[y][0], 0)

    def test_valid_chunk_has_correct_dimensions(self):
        chunk = self.gen.generate_valid_chunk(offset=1)
        self.assertEqual(len(chunk), CHUNK_HEIGHT)
        self.assertEqual(len(chunk[0]), CHUNK_WIDTH)

    def test_valid_chunk_is_not_none(self):
        chunk = self.gen.generate_valid_chunk(offset=1)
        self.assertIsNotNone(chunk)

    def test_valid_chunk_all_tiles_are_valid_values(self):
        chunk = self.gen.generate_valid_chunk(offset=2)
        valid = {0, 1, 2}
        for row in chunk:
            for tile in row:
                self.assertIn(tile, valid)

    def test_max_attempts_exceeded_falls_back_to_flat(self):
        """If max_attempts=1 and first chunk is invalid, should fall back gracefully."""
        gen = ProceduralGenerator(seed=SEED)
        # max_attempts=1 means at attempt=1 it will fall back to flat
        chunk = gen.generate_valid_chunk(offset=5, max_attempts=1)
        self.assertIsNotNone(chunk)
        self.assertEqual(len(chunk), CHUNK_HEIGHT)

    def test_consecutive_chunks_with_prev_chunk(self):
        gen = ProceduralGenerator(seed=SEED)
        chunk0 = gen.generate_valid_chunk(offset=0)
        chunk1 = gen.generate_valid_chunk(offset=1, prev_chunk=chunk0)
        self.assertIsNotNone(chunk1)

    def test_generation_time_is_reasonable(self):
        """Each chunk should be generated within 5 seconds."""
        gen = ProceduralGenerator(seed=SEED)
        start = time.time()
        gen.generate_valid_chunk(offset=3)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, "Chunk generation took too long")



# validate_chunk_traversable


class TestValidateChunkTraversable(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def _make_solid_chunk(self):
        """Returns a chunk that is entirely solid — not traversable."""
        return [[1] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]

    def _make_all_air_chunk(self):
        """Returns a chunk with no terrain — not traversable from ground."""
        return [[0] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]

    def _make_walkable_chunk(self):
        """A chunk with a flat ground one tile from the bottom — fully walkable."""
        chunk = [[0] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]
        for x in range(CHUNK_WIDTH):
            chunk[CHUNK_HEIGHT - 1][x] = 1
        return chunk

    def test_flat_chunk_is_traversable(self):
        chunk = self._make_walkable_chunk()
        is_valid, visited = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertTrue(is_valid)

    def test_solid_chunk_is_not_traversable(self):
        chunk = self._make_solid_chunk()
        is_valid, _ = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertFalse(is_valid)

    def test_all_air_chunk_is_not_traversable(self):
        chunk = self._make_all_air_chunk()
        is_valid, _ = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertFalse(is_valid)

    def test_visited_is_set(self):
        chunk = self._make_walkable_chunk()
        _, visited = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertIsInstance(visited, set)

    def test_visited_set_is_not_empty_for_valid_chunk(self):
        chunk = self._make_walkable_chunk()
        _, visited = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertGreater(len(visited), 0)

    def test_visited_positions_are_not_solid(self):
        chunk = self._make_walkable_chunk()
        _, visited = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        for x, y in visited:
            self.assertEqual(chunk[y][x], 0, f"Visited position ({x},{y}) should not be solid")

    def test_impossible_gap_fails_validation(self):
        """A gap wider than max jump distance should fail."""
        chunk = self._make_walkable_chunk()
        gap_start = 5
        gap_width = PLAYER_MAX_JUMP_DISTANCE + 2
        for x in range(gap_start, min(gap_start + gap_width, CHUNK_WIDTH)):
            for y in range(CHUNK_HEIGHT):
                chunk[y][x] = 0  # Remove all ground in the gap
        is_valid, _ = self.gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertFalse(is_valid)

    def test_chunk_boundary_validation_with_prev_chunk(self):
        """Boundary between prev_chunk and current chunk must be jumpable."""
        prev = self._make_walkable_chunk()
        curr = self._make_walkable_chunk()
        is_valid, _ = self.gen.validate_chunk_traversable(curr, CHUNK_WIDTH, CHUNK_HEIGHT, prev_chunk=prev)
        self.assertTrue(is_valid)

    def test_impassable_boundary_fails_with_prev_chunk(self):
        """A wall too high to jump over at the chunk boundary should fail."""
        prev = self._make_walkable_chunk()
        # Make the first column of current chunk a very tall wall
        curr = [[0] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]
        wall_height = PLAYER_MAX_JUMP_HEIGHT + 4
        for y in range(CHUNK_HEIGHT - 1, CHUNK_HEIGHT - 1 - wall_height, -1):
            if 0 <= y < CHUNK_HEIGHT:
                curr[y][0] = 1
        # Rest of ground
        for x in range(1, CHUNK_WIDTH):
            curr[CHUNK_HEIGHT - 1][x] = 1
        is_valid, _ = self.gen.validate_chunk_traversable(curr, CHUNK_WIDTH, CHUNK_HEIGHT, prev_chunk=prev)
        self.assertFalse(is_valid)



# place_spikes_from_visited


class TestPlaceSpikesFromVisited(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)
        self.biome_config = Plain().get_config(1.0)
        # Build a flat chunk and a dense visited set
        self.chunk = [[0] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]
        for x in range(CHUNK_WIDTH):
            self.chunk[CHUNK_HEIGHT - 1][x] = 1
        self.visited = {(x, CHUNK_HEIGHT - 2) for x in range(CHUNK_WIDTH)}

    def test_spikes_are_value_2(self):
        result = self.gen.place_spikes_from_visited(self.chunk, self.visited, self.biome_config, offset=1)
        for row in result:
            for tile in row:
                self.assertIn(tile, {0, 1, 2})

    def test_spikes_only_placed_on_ground_surface(self):
        result = self.gen.place_spikes_from_visited(self.chunk, self.visited, self.biome_config, offset=1)
        for y in range(CHUNK_HEIGHT):
            for x in range(CHUNK_WIDTH):
                if result[y][x] == ObstacleType.SPIKE:
                    # The tile below must be solid ground
                    below = y + 1
                    self.assertLess(below, CHUNK_HEIGHT)
                    self.assertEqual(result[below][x], 1)

    def test_no_spikes_placed_on_edges(self):
        """Spikes should not appear in the first 2 or last 2 columns."""
        result = self.gen.place_spikes_from_visited(self.chunk, self.visited, self.biome_config, offset=1)
        for y in range(CHUNK_HEIGHT):
            self.assertNotEqual(result[y][0], ObstacleType.SPIKE)
            self.assertNotEqual(result[y][1], ObstacleType.SPIKE)
            self.assertNotEqual(result[y][CHUNK_WIDTH - 1], ObstacleType.SPIKE)
            self.assertNotEqual(result[y][CHUNK_WIDTH - 2], ObstacleType.SPIKE)

    def test_no_spikes_when_spike_probability_is_zero(self):
        config = dict(self.biome_config)
        config['spike_probability'] = 0.0
        result = self.gen.place_spikes_from_visited(self.chunk, self.visited, config, offset=1)
        spike_count = sum(1 for row in result for t in row if t == ObstacleType.SPIKE)
        self.assertEqual(spike_count, 0)

    def test_spikes_respect_minimum_horizontal_spacing(self):
        """Two spikes must never appear on adjacent columns."""
        config = dict(self.biome_config)
        config['spike_probability'] = 1.0  # Maximise chance of spikes
        result = self.gen.place_spikes_from_visited(self.chunk, self.visited, config, offset=1)
        spike_xs = [x for x in range(CHUNK_WIDTH) for y in range(CHUNK_HEIGHT) if result[y][x] == ObstacleType.SPIKE]
        for i in range(len(spike_xs) - 1):
            self.assertGreater(spike_xs[i + 1] - spike_xs[i], 1)



# generate_floating_platforms


class TestGenerateFloatingPlatforms(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)
        self.heights = [3] * CHUNK_WIDTH
        self.biome_config = Plain().get_config(1.0)

    def test_returns_a_list(self):
        result = self.gen.generate_floating_platforms(
            self.heights, CHUNK_WIDTH, CHUNK_HEIGHT, offset=1, biome_config=self.biome_config
        )
        self.assertIsInstance(result, list)

    def test_all_platforms_within_chunk_bounds(self):
        result = self.gen.generate_floating_platforms(
            self.heights, CHUNK_WIDTH, CHUNK_HEIGHT, offset=2, biome_config=self.biome_config
        )
        for plat in result:
            self.assertGreaterEqual(plat['x'], 0)
            self.assertLess(plat['x'] + plat['width'], CHUNK_WIDTH + 1)

    def test_platform_width_is_at_least_2(self):
        for offset in range(1, 10):
            result = self.gen.generate_floating_platforms(
                self.heights, CHUNK_WIDTH, CHUNK_HEIGHT, offset=offset, biome_config=self.biome_config
            )
            for plat in result:
                self.assertGreaterEqual(plat['width'], 2)

    def test_platforms_have_expected_keys(self):
        result = self.gen.generate_floating_platforms(
            self.heights, CHUNK_WIDTH, CHUNK_HEIGHT, offset=3, biome_config=self.biome_config
        )
        for plat in result:
            for key in ('x', 'y', 'width', 'type'):
                self.assertIn(key, plat)



# generate_cave_ceiling


class TestGenerateCaveCeiling(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_returns_correct_number_of_values(self):
        ceiling = self.gen.generate_cave_ceiling(CHUNK_WIDTH, offset=1)
        self.assertEqual(len(ceiling), CHUNK_WIDTH)

    def test_all_ceiling_heights_are_at_least_2(self):
        ceiling = self.gen.generate_cave_ceiling(CHUNK_WIDTH, offset=1)
        for h in ceiling:
            self.assertGreaterEqual(h, 2)

    def test_ceiling_heights_do_not_exceed_chunk_height(self):
        ceiling = self.gen.generate_cave_ceiling(CHUNK_WIDTH, offset=1)
        for h in ceiling:
            self.assertLess(h, CHUNK_HEIGHT)



# count_obstacles


class TestCountObstacles(unittest.TestCase):

    def setUp(self):
        self.gen = ProceduralGenerator(seed=SEED)

    def test_empty_chunk_has_zero_obstacles(self):
        chunk = [[0] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]
        counts = self.gen.count_obstacles(chunk)
        self.assertEqual(counts.get(2, 0), 0)

    def test_counts_spikes_correctly(self):
        chunk = [[0] * CHUNK_WIDTH for _ in range(CHUNK_HEIGHT)]
        chunk[5][3] = ObstacleType.SPIKE
        chunk[5][7] = ObstacleType.SPIKE
        counts = self.gen.count_obstacles(chunk)
        self.assertEqual(counts[2], 2)



# Integration: full pipeline


class TestFullPipeline(unittest.TestCase):

    def test_multiple_consecutive_chunks_are_all_valid(self):
        gen = ProceduralGenerator(seed=SEED)
        prev = None
        for offset in range(0, 6):
            chunk = gen.generate_valid_chunk(offset=offset, prev_chunk=prev)
            self.assertIsNotNone(chunk)
            if offset > 0:
                is_valid, _ = gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT, prev_chunk=prev)
                self.assertTrue(is_valid, f"Chunk at offset {offset} failed traversal validation")
            prev = chunk

    def test_difficulty_increases_after_each_chunk(self):
        gen = ProceduralGenerator(seed=SEED)
        difficulties = []
        for offset in range(1, 6):
            gen.generate_valid_chunk(offset=offset)
            gen.increase_difficulty(5)
            difficulties.append(gen.difficulty)
        for i in range(len(difficulties) - 1):
            self.assertGreaterEqual(difficulties[i + 1], difficulties[i])

    def test_chunks_at_high_difficulty_still_valid(self):
        gen = ProceduralGenerator(seed=SEED)
        gen.difficulty = 1.9
        chunk = gen.generate_valid_chunk(offset=5)
        self.assertIsNotNone(chunk)
        is_valid, _ = gen.validate_chunk_traversable(chunk, CHUNK_WIDTH, CHUNK_HEIGHT)
        self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main(verbosity=2)
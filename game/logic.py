
def generate_chunk(width=20, height=15):
    import random
    # Generate a chunk of the map with ground at the bottom
    chunk = [[0 for x in range(width)] for y in range(height)]

    # Fill the bottom row with ground blocks
    for x in range(width):
        chunk[height-1][x] = 1

    chunk[random.randint(0,height-1)][random.randint(0,width-1)] = 1



    return chunk


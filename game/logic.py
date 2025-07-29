WIDTH = 20
HEIGHT = 10

def generate_map():
    chunk = []
    for x in range(WIDTH):
        col = []
        for y in range(HEIGHT):
            if y == HEIGHT - 1:
                col.append(1)  # ground
            else:
                col.append(0)  # air
        chunk.append(col)
    return chunk

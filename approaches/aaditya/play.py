import os
import time

from tetris_footprint import TetrisGame, SHAPES, get_rotation_count, get_cells

SLEEP_SECONDS = 0.6
MAX_PIECES = None  # None = run until no placement is possible (game over)


def find_drop_row(board, piece_type, rotation, origin_col):
    """Hard-drop simulation for one (rotation, column): returns the lowest
    origin_row this placement can reach, or None if it can't be placed at
    all (column already blocked at the top)."""
    last_valid_row = None
    for origin_row in range(board.height):
        if board.can_place(piece_type, rotation, origin_row, origin_col):
            last_valid_row = origin_row
        elif last_valid_row is not None:
            # board only gets more solid going down, so once a row after a
            # valid one collides, every row below it will collide too
            break
    return last_valid_row


def count_new_holes(board, cells):
    """Empty board cells that would end up trapped under this placement --
    i.e. columns where the piece rests above the existing stack, leaving a
    gap that can never be filled again."""
    bottom_in_col = {}
    for r, c in cells:
        bottom_in_col[c] = max(bottom_in_col.get(c, r), r)

    holes = 0
    for c, piece_bottom in bottom_in_col.items():
        stack_top = board.height  # sentinel: column currently empty
        for r in range(board.height):
            if board.grid[r][c] is not None:
                stack_top = r
                break
        holes += max(0, stack_top - piece_bottom - 1)
    return holes


def best_placement(game):
    """
    For the current piece:
      1. Enumerate every (rotation, column) pair and hard-drop it to its
         resting row -- these are the 'bottommost positions'.
      2. Keep only the placement(s) reaching the least height (the piece's
         topmost cell ends up as low/flat as possible).
      3. Break ties by least hollowness (fewest newly trapped empty cells).
      4. Break any remaining ties by taking the first one found.
    Returns (rotation, origin_row, origin_col), or None if the piece has
    nowhere to go (game over).
    """
    board = game.board
    piece_type = game.current_piece

    candidates = []
    for rotation in range(get_rotation_count(piece_type)):
        offsets = SHAPES[piece_type][rotation]
        min_c = min(o[1] for o in offsets)
        max_c = max(o[1] for o in offsets)
        for origin_col in range(-min_c, board.width - max_c):
            origin_row = find_drop_row(board, piece_type, rotation, origin_col)
            if origin_row is None:
                continue
            cells = get_cells(piece_type, rotation, origin_row, origin_col)
            top_row = min(r for r, _ in cells)
            height_reached = board.height - top_row
            holes = count_new_holes(board, cells)
            candidates.append((height_reached, holes, rotation, origin_row, origin_col))

    if not candidates:
        return None

    candidates.sort(key=lambda c: (c[0], c[1]))
    _, _, rotation, origin_row, origin_col = candidates[0]
    return rotation, origin_row, origin_col


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def run(sleep_seconds=SLEEP_SECONDS, max_pieces=MAX_PIECES):
    game = TetrisGame()
    placed = 0

    while max_pieces is None or placed < max_pieces:
        placement = best_placement(game)
        if placement is None:
            clear_screen()
            print(game.render())
            print("\nNo valid placement left -- game over.")
            break

        rotation, origin_row, origin_col = placement
        result = game.place_current(rotation, origin_row, origin_col)
        placed += 1

        clear_screen()
        print(game.render())
        if result["lines_cleared"]:
            print(f"\nCleared {result['lines_cleared']} line(s)!")

        time.sleep(sleep_seconds)


if __name__ == "__main__":
    run()
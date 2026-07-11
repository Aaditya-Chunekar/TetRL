"""
Tetris "footprint" module — text-based, non-gravity Tetris.

This file gives you everything EXCEPT the control loop / placement-search logic:

    - Piece shapes + rotations           (SHAPES)
    - Board grid + collision checking    (Board.can_place)
    - Locking a piece onto the board     (Board.place)
    - Standard line-clear logic          (Board.clear_lines)
    - 7-bag next-piece sequencer         (TetrisGame.current_piece / .next_piece)
    - A renderer that draws every placed piece with a smooth Unicode box-drawing
      border (the same character set `tree` uses: │ ─ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼) and a
      distinct ANSI color per piece type, so pieces stay visually separate even
      after they're locked in.

You write:
    - The loop that asks the user (or your search code) for a rotation + column/row
    - Trying placements / testing possibilities
    - Calling game.place_current(...) and game.render() when you're ready

Windows terminals: run once at program start if colors show as raw escape codes:
    os.system("")   # enables ANSI escape processing on Windows 10+ cmd
"""

import os
import random
from collections import deque

os.system("")  # harmless on Linux/Mac, enables ANSI on Windows cmd

# --------------------------------------------------------------------------
# Colors
# --------------------------------------------------------------------------

class Color:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    PURPLE = "\033[95m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    ORANGE = "\033[38;5;208m"
    GRAY = "\033[90m"

PIECE_COLORS = {
    "I": Color.CYAN,
    "O": Color.YELLOW,
    "T": Color.PURPLE,
    "S": Color.GREEN,
    "Z": Color.RED,
    "J": Color.BLUE,
    "L": Color.ORANGE,
}

# --------------------------------------------------------------------------
# Piece definitions: piece_type -> list of rotation states,
# each rotation state is a list of (row, col) offsets from an anchor (0,0).
# Not official SRS (no wall-kicks needed since placement is manual, not falling).
# --------------------------------------------------------------------------

SHAPES = {
    "I": [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 0), (1, 0), (2, 0), (3, 0)],
    ],
    "O": [
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    ],
    "T": [
        [(0, 0), (0, 1), (0, 2), (1, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (0, 1)],
        [(0, 0), (1, 0), (2, 0), (1, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (0, 1), (1, 0), (2, 0)],
        [(0, 0), (0, 1), (0, 2), (1, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 0), (1, 0), (2, 0), (2, 1)],
        [(0, 0), (0, 1), (0, 2), (1, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}


def get_rotation_count(piece_type):
    return len(SHAPES[piece_type])


def get_cells(piece_type, rotation, origin_row, origin_col):
    """Absolute board cells this piece occupies at a given anchor + rotation."""
    offsets = SHAPES[piece_type][rotation % len(SHAPES[piece_type])]
    return [(origin_row + dr, origin_col + dc) for dr, dc in offsets]


# --------------------------------------------------------------------------
# Board
# --------------------------------------------------------------------------

class Board:
    def __init__(self, width=10, height=20):
        self.width = width
        self.height = height
        # each cell is None (empty) or (piece_id, piece_type)
        self.grid = [[None] * width for _ in range(height)]
        self._next_piece_id = 0

    def in_bounds(self, r, c):
        return 0 <= r < self.height and 0 <= c < self.width

    def can_place(self, piece_type, rotation, origin_row, origin_col):
        """Collision check only. Call this as many times as you like while
        you search/test candidate placements — it never mutates the board."""
        for r, c in get_cells(piece_type, rotation, origin_row, origin_col):
            if not self.in_bounds(r, c):
                return False
            if self.grid[r][c] is not None:
                return False
        return True

    def place(self, piece_type, rotation, origin_row, origin_col):
        """Locks the piece onto the board if the placement is legal.
        Returns True on success, False if the placement was invalid."""
        if not self.can_place(piece_type, rotation, origin_row, origin_col):
            return False
        pid = self._next_piece_id
        self._next_piece_id += 1
        for r, c in get_cells(piece_type, rotation, origin_row, origin_col):
            self.grid[r][c] = (pid, piece_type)
        return True

    def clear_lines(self):
        """Standard full-row clear. Returns number of rows cleared."""
        remaining = [row for row in self.grid if any(cell is None for cell in row)]
        cleared = self.height - len(remaining)
        for _ in range(cleared):
            remaining.insert(0, [None] * self.width)
        self.grid = remaining
        return cleared

    def column_heights(self):
        """Convenience: height of stack in each column (0 = empty column).
        Useful if your placement-search logic wants quick board metrics."""
        heights = [0] * self.width
        for c in range(self.width):
            for r in range(self.height):
                if self.grid[r][c] is not None:
                    heights[c] = self.height - r
                    break
        return heights


# --------------------------------------------------------------------------
# 7-bag next-piece sequencer
# --------------------------------------------------------------------------

class TetrisGame:
    def __init__(self, width=10, height=20):
        self.board = Board(width, height)
        self._bag = []
        self._queue = deque()
        self._fill_queue(2)
        self.lines_cleared_total = 0
        self.pieces_placed = 0

    def _new_bag(self):
        bag = list(SHAPES.keys())
        random.shuffle(bag)
        return bag

    def _fill_queue(self, n):
        while len(self._queue) < n:
            if not self._bag:
                self._bag = self._new_bag()
            self._queue.append(self._bag.pop())

    @property
    def current_piece(self):
        self._fill_queue(2)
        return self._queue[0]

    @property
    def next_piece(self):
        self._fill_queue(2)
        return self._queue[1]

    def place_current(self, rotation, origin_row, origin_col):
        """Attempt to place the CURRENT piece. On success, advances the
        sequencer (current -> discarded, next -> becomes current) and clears
        any full lines. Returns a result dict; does nothing to the queue on
        failure so you can retry with a different rotation/position."""
        piece_type = self.current_piece
        if not self.board.place(piece_type, rotation, origin_row, origin_col):
            return {"success": False, "piece": piece_type, "lines_cleared": 0}

        self._queue.popleft()
        self._fill_queue(2)
        cleared = self.board.clear_lines()
        self.lines_cleared_total += cleared
        self.pieces_placed += 1
        return {"success": True, "piece": piece_type, "lines_cleared": cleared}

    def render(self):
        return render_frame(self)


# --------------------------------------------------------------------------
# Renderer: smooth Unicode box-drawing borders + per-piece color
# --------------------------------------------------------------------------

def _group_id(get_cell, h, w, r, c):
    if r < 0 or r >= h or c < 0 or c >= w:
        return "OUT"
    cell = get_cell(r, c)
    return "EMPTY" if cell is None else cell[0]


def _box_char(up, down, left, right):
    if not (up or down or left or right):
        return " "
    if up and down and left and right:
        return "┼"
    if up and down and left:
        return "┤"
    if up and down and right:
        return "├"
    if left and right and up:
        return "┴"
    if left and right and down:
        return "┬"
    if up and down:
        return "│"
    if left and right:
        return "─"
    if up and left:
        return "┘"
    if up and right:
        return "└"
    if down and left:
        return "┐"
    if down and right:
        return "┌"
    if up or down:
        return "│"
    return "─"


def _render_grid(get_cell, h, w, cell_width=3):
    """Generic renderer: get_cell(r, c) -> None or (group_id, piece_type).
    Draws a wall between two adjacent cells whenever their group ids differ,
    which is what makes each locked piece keep a visible, separate outline."""

    def gid(r, c):
        return _group_id(get_cell, h, w, r, c)

    # horiz_seg[i][c]: wall between cell (i-1, c) and cell (i, c)
    horiz_seg = [[gid(i - 1, c) != gid(i, c) for c in range(w)] for i in range(h + 1)]
    # vert_seg[r][j]: wall between cell (r, j-1) and cell (r, j)
    vert_seg = [[gid(r, j - 1) != gid(r, j) for j in range(w + 1)] for r in range(h)]

    def intersection(i, j):
        up = vert_seg[i - 1][j] if i - 1 >= 0 else False
        down = vert_seg[i][j] if i < h else False
        left = horiz_seg[i][j - 1] if j - 1 >= 0 else False
        right = horiz_seg[i][j] if j < w else False
        return _box_char(up, down, left, right)

    fill = "─" * cell_width
    gap = " " * cell_width
    lines = []
    for i in range(h + 1):
        row = []
        for j in range(w + 1):
            row.append(intersection(i, j))
            if j < w:
                row.append(fill if horiz_seg[i][j] else gap)
        lines.append("".join(row))

        if i < h:
            row = []
            for j in range(w + 1):
                row.append("│" if vert_seg[i][j] else " ")
                if j < w:
                    cell = get_cell(i, j)
                    if cell is None:
                        row.append(" " * cell_width)
                    else:
                        _, piece_type = cell
                        color = PIECE_COLORS.get(piece_type, "")
                        text = piece_type.center(cell_width)
                        row.append(f"{color}{text}{Color.RESET}")
            lines.append("".join(row))
    return "\n".join(lines)


def render_board(board):
    return _render_grid(lambda r, c: board.grid[r][c], board.height, board.width)


def render_piece_preview(piece_type, rotation=0):
    """Small standalone box for the next-piece sequencer display."""
    offsets = SHAPES[piece_type][rotation % len(SHAPES[piece_type])]
    max_r = max(o[0] for o in offsets) + 1
    max_c = max(o[1] for o in offsets) + 1
    mini = [[None] * max_c for _ in range(max_r)]
    for r, c in offsets:
        mini[r][c] = (0, piece_type)  # single group id -> one solid outline
    return _render_grid(lambda r, c: mini[r][c], max_r, max_c, cell_width=2)


def render_frame(game):
    """Full frame: next-piece sequencer (top-left) + board + basic stats."""
    header = f"NEXT: {game.next_piece}"
    preview = render_piece_preview(game.next_piece)
    stats = (
        f"Lines cleared: {game.lines_cleared_total}   "
        f"Pieces placed: {game.pieces_placed}   "
        f"Now placing: {Color.GRAY}{game.current_piece}{Color.RESET}"
    )
    board_str = render_board(game.board)
    return f"{header}\n{preview}\n\n{stats}\n\n{board_str}"


# --------------------------------------------------------------------------
# Minimal smoke test (does NOT implement placement search / input handling —
# that part is yours to write, per your request). This just proves the
# footprint renders and locks pieces correctly.
# --------------------------------------------------------------------------

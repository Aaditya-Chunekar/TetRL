# TetRL

A text-based, non-gravity implementation of Tetris in Python. Pieces don't fall on a
timer — placement is decided by code (currently a greedy heuristic, with a
reinforcement-learning agent planned) and locked in immediately, one piece at a time.

## Status: in development

Core engine and a working heuristic auto-player are functional. This is not a
finished project — see [Planned work](#planned-work) below.

## Features

- Full tetromino set (I, O, T, S, Z, J, L) with all rotation states
- Collision detection and line-clear logic
- 7-bag next-piece sequencer, shown top-left of the board
- Board renderer using Unicode box-drawing characters (`┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼`) so
  each locked piece keeps a visible, separate outline instead of merging into a flat grid
- ANSI color per piece type
- Configurable pause before a completed line clears, so the full row is visible before
  it disappears

## Files

| File | Purpose |
|---|---|
| `tetris_footprint.py` | Core engine: piece shapes, board, collision checking, placement, line clearing, rendering |
| `play.py` | Greedy heuristic auto-player built on top of the footprint |

## Running it

Requires Python 3.8+, standard library only.

```
python3 play.py
```

Runs until no placement is possible (game over). Tune `SLEEP_SECONDS` and
`LINE_CLEAR_PAUSE` at the top of `play.py` to change playback speed.

## Placement algorithm (current)

For each new piece, `play.py` evaluates every `(rotation, column)` combination:

1. Hard-drops each combination to its resting row.
2. Keeps the placement(s) that reach the least height (piece's topmost cell ends up
   as low as possible).
3. Breaks ties by fewest new holes created (empty cells sealed under the piece).
4. Breaks any remaining ties by taking the first option found.

This is a single-piece greedy heuristic — it only considers the current piece, not the
next one in the queue, and only scores holes created by that one placement rather than
total board holes.

## Results (current heuristic)
 
Measured as lines cleared per piece placed, across 500 full games (each run until game
over):
 
| | Value |
|---|---|
| Max | 0.3291 |
| Min | 0.0600 |
| Avg | 0.2425 |
 
These numbers reflect the greedy, single-piece-lookahead heuristic above — they're a
baseline to compare the planned RL agent against, not a final result.

## Planned work

- Reinforcement-learning agent to replace/augment the heuristic placer
- Look-ahead placement using the next-piece preview, not just the current piece
- Full-board hole scoring instead of per-placement hole scoring
- Manual/interactive placement mode
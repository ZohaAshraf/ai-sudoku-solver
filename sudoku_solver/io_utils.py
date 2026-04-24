"""
io_utils.py — Input / Output utilities for the Sudoku solver
Handles file parsing, grid formatting, and pretty-printing.
"""

import os
from pathlib import Path


# ------------------------------------------------------------------ #
#  Parsing                                                             #
# ------------------------------------------------------------------ #

def load_grid_from_file(path: str | Path) -> list[list[int]]:
    """
    Parse a Sudoku grid from a text file.
    Expected format: 9 lines, each containing 9 digits (0 = empty).
    Whitespace between digits is optional.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Puzzle file not found: {path}")

    grid = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            digits = [int(ch) for ch in line if ch.isdigit()]
            if len(digits) == 9:
                grid.append(digits)

    if len(grid) != 9:
        raise ValueError(
            f"Expected 9 rows in '{path}', got {len(grid)}."
        )
    return grid


def load_grid_from_string(text: str) -> list[list[int]]:
    """Parse a grid from a multi-line string (same format as file)."""
    lines = [l.strip() for l in text.strip().splitlines()]
    grid = []
    for line in lines:
        if not line or line.startswith("#"):
            continue
        digits = [int(ch) for ch in line if ch.isdigit()]
        if len(digits) == 9:
            grid.append(digits)
    if len(grid) != 9:
        raise ValueError(f"Expected 9 rows, got {len(grid)}.")
    return grid


# ------------------------------------------------------------------ #
#  Display                                                             #
# ------------------------------------------------------------------ #

_H_LINE = "+-------+-------+-------+"
_ROW_FMT = "| {} {} {} | {} {} {} | {} {} {} |"


def format_grid(grid: list[list[int]], original: list[list[int]] | None = None) -> str:
    """
    Render a 9×9 grid as a Unicode box-drawing string.
    If *original* is provided, zeros in the original are shown as '·' (clue vs solved).
    """
    lines = [_H_LINE]
    for r, row in enumerate(grid):
        if r > 0 and r % 3 == 0:
            lines.append(_H_LINE)
        cells = []
        for c, val in enumerate(row):
            if val == 0:
                cells.append("·")
            else:
                cells.append(str(val))
        lines.append(_ROW_FMT.format(*cells))
    lines.append(_H_LINE)
    return "\n".join(lines)


def print_grid(grid: list[list[int]], title: str = "") -> None:
    """Print a formatted grid with an optional title."""
    if title:
        print(f"\n{'─' * 27}")
        print(f"  {title}")
        print(f"{'─' * 27}")
    print(format_grid(grid))


def print_comparison(original: list[list[int]], solved: list[list[int]], title: str = "") -> None:
    """Print original and solved grids side-by-side."""
    if title:
        print(f"\n{'═' * 58}")
        print(f"  {title}")
        print(f"{'═' * 58}")

    orig_lines  = format_grid(original).splitlines()
    solve_lines = format_grid(solved).splitlines()

    print(f"  {'PUZZLE':^27}    {'SOLUTION':^27}")
    for ol, sl in zip(orig_lines, solve_lines):
        print(f"  {ol}    {sl}")


# ------------------------------------------------------------------ #
#  Validation                                                          #
# ------------------------------------------------------------------ #

def is_valid_solution(grid: list[list[int]]) -> bool:
    """Verify that a completed grid satisfies all Sudoku constraints."""
    expected = set(range(1, 10))

    # Rows
    for row in grid:
        if set(row) != expected:
            return False
    # Columns
    for c in range(9):
        if {grid[r][c] for r in range(9)} != expected:
            return False
    # Boxes
    for br in range(3):
        for bc in range(3):
            vals = {
                grid[br * 3 + dr][bc * 3 + dc]
                for dr in range(3) for dc in range(3)
            }
            if vals != expected:
                return False
    return True

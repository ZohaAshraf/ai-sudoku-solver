"""
main.py — Entry point for Sudoku Premium
Launches the GUI game, or CLI solver for batch use.
"""

import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def launch_gui():
    from game_gui import main as gui_main
    gui_main()


def cli_solve(difficulty=None, file_path=None):
    import time
    from solver import SudokuSolver

    PUZZLES = {
        "easy":     BASE_DIR / "puzzles" / "easy.txt",
        "medium":   BASE_DIR / "puzzles" / "medium.txt",
        "hard":     BASE_DIR / "puzzles" / "hard.txt",
        "veryhard": BASE_DIR / "puzzles" / "veryhard.txt",
    }

    def load_grid(path):
        grid = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                digits = [int(ch) for ch in line if ch.isdigit()]
                if len(digits) == 9:
                    grid.append(digits)
        return grid

    def solve_one(name, path):
        grid = load_grid(path)
        t0   = time.perf_counter()
        res  = SudokuSolver(grid).solve()
        elapsed = time.perf_counter() - t0
        status = "✓ SOLVED" if res.success else "✗ FAILED"
        print(f"  {status}  {name:<12}  {elapsed*1000:>7.1f} ms  "
              f"backtracks={res.stats['backtrack_calls']}")

    if file_path:
        p = Path(file_path)
        solve_one(p.stem, p)
    elif difficulty:
        solve_one(difficulty, PUZZLES[difficulty])
    else:
        print("\n  CSP Sudoku Premium — Batch Solver")
        print("  " + "─"*46)
        for name, path in PUZZLES.items():
            solve_one(name, path)
        print()


def parse_args():
    p = argparse.ArgumentParser(description="Sudoku Premium — CSP Solver + GUI Game")
    p.add_argument("--gui",    action="store_true", help="Launch GUI game (default)")
    p.add_argument("--all",    action="store_true", help="CLI: solve all puzzles")
    p.add_argument("--puzzle", choices=["easy","medium","hard","veryhard"],
                   help="CLI: solve a specific puzzle")
    p.add_argument("--file",   type=str, help="CLI: path to custom puzzle file")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.all:
        cli_solve()
    elif args.puzzle:
        cli_solve(difficulty=args.puzzle)
    elif args.file:
        cli_solve(file_path=args.file)
    else:
        launch_gui()

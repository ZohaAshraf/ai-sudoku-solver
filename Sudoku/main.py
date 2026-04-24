"""
main.py — CLI & GUI entry point for the CSP Sudoku Solver/Game
Supports:
  - Interactive GUI game (Tkinter)
  - Interactive CLI menu
  - Batch solving
  - Custom file loading
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from solver import SudokuSolver
from io_utils import load_grid_from_file, print_grid, print_comparison, is_valid_solution

# ─────────────────────────────────────────────────────────────────────────────
#  ANSI colour helpers
# ─────────────────────────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

GREEN  = lambda t: _c("92", t)
YELLOW = lambda t: _c("93", t)
CYAN   = lambda t: _c("96", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)
RED    = lambda t: _c("91", t)

# ─────────────────────────────────────────────────────────────────────────────
#  Puzzle registry
# ─────────────────────────────────────────────────────────────────────────────
PUZZLES_DIR = Path(__file__).parent / "puzzles"

PUZZLE_REGISTRY = {
    "easy":     PUZZLES_DIR / "easy.txt",
    "medium":   PUZZLES_DIR / "medium.txt",
    "hard":     PUZZLES_DIR / "hard.txt",
    "veryhard": PUZZLES_DIR / "veryhard.txt",
}

DIFFICULTY_EMOJI = {
    "easy":     "🟢",
    "medium":   "🟡",
    "hard":     "🔴",
    "veryhard": "⚫",
}

# ─────────────────────────────────────────────────────────────────────────────
#  Core solve routine
# ─────────────────────────────────────────────────────────────────────────────

def solve_puzzle(name: str, path: Path, verbose: bool = True) -> dict:
    """Load, solve, and optionally display a single puzzle. Returns metrics."""
    grid = load_grid_from_file(path)
    solver = SudokuSolver(grid)

    if verbose:
        emoji = DIFFICULTY_EMOJI.get(name, "🔵")
        print(f"\n{BOLD(f'{emoji}  Solving: {name.upper()}')}")
        print(DIM(f"   File: {path}"))

    t0 = time.perf_counter()
    result = solver.solve()
    elapsed = time.perf_counter() - t0

    metrics = {
        "name": name,
        "time_s": elapsed,
        "backtracks": result.stats["backtrack_calls"],
        "failures": result.stats["failures"],
        "success": result.success,
    }

    if verbose:
        if result.success:
            valid = is_valid_solution(result.solution)
            print_comparison(grid, result.solution, title=f"{name.title()} — Solved")
            print(f"\n  {GREEN('✓ SOLVED')}  |  "
                  f"Time: {YELLOW(f'{elapsed*1000:.1f} ms')}  |  "
                  f"Backtracks: {CYAN(str(result.stats['backtrack_calls']))}  |  "
                  f"Failures: {CYAN(str(result.stats['failures']))}  |  "
                  f"Valid: {GREEN('YES') if valid else RED('NO')}")
        else:
            print(RED("  ✗ NO SOLUTION FOUND"))

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
#  Batch mode
# ─────────────────────────────────────────────────────────────────────────────

def run_all(verbose: bool = True) -> list[dict]:
    all_metrics = []
    for name, path in PUZZLE_REGISTRY.items():
        m = solve_puzzle(name, path, verbose=verbose)
        all_metrics.append(m)
    _print_summary(all_metrics)
    return all_metrics


def _print_summary(metrics: list[dict]) -> None:
    w = 60
    print(f"\n{'═' * w}")
    print(BOLD(f"  {'PERFORMANCE SUMMARY':^{w-4}}"))
    print(f"{'═' * w}")
    header = f"  {'Puzzle':<12}{'Time (ms)':>12}{'Backtracks':>14}{'Failures':>12}{'Status':>8}"
    print(BOLD(header))
    print(f"{'─' * w}")
    for m in metrics:
        status = GREEN("✓") if m["success"] else RED("✗")
        emoji = DIFFICULTY_EMOJI.get(m["name"], "")
        print(
            f"  {emoji} {m['name']:<10}"
            f"{m['time_s']*1000:>12.1f}"
            f"{m['backtracks']:>14}"
            f"{m['failures']:>12}"
            f"  {status:>8}"
        )
    print(f"{'═' * w}")
    print(f"\n  {BOLD('Difficulty Analysis:')}")
    if len(metrics) >= 2:
        easy  = next((m for m in metrics if m["name"] == "easy"), None)
        vhard = next((m for m in metrics if m["name"] == "veryhard"), None)
        if easy and vhard and easy["backtracks"] > 0:
            ratio = vhard["backtracks"] / max(easy["backtracks"], 1)
            print(f"  • Very Hard requires ~{ratio:.0f}× more backtracks than Easy")
    print(f"  • MRV + AC-3 dramatically reduce search space")
    print(f"  • LCV ordering minimises domain wipeouts\n")


# ─────────────────────────────────────────────────────────────────────────────
#  Interactive CLI menu
# ─────────────────────────────────────────────────────────────────────────────

def interactive_menu() -> None:
    BANNER = r"""
  ╔══════════════════════════════════════════╗
  ║   CSP SUDOKU SOLVER  — v2.0              ║
  ║   Backtracking · AC-3 · MRV · LCV        ║
  ╚══════════════════════════════════════════╝
"""
    print(CYAN(BANNER))
    while True:
        print(BOLD("  Choose an option:"))
        print("  [1] Solve Easy")
        print("  [2] Solve Medium")
        print("  [3] Solve Hard")
        print("  [4] Solve Very Hard")
        print("  [5] Solve ALL puzzles")
        print("  [6] Load custom puzzle file")
        print("  [G] Launch GUI Game")
        print("  [0] Exit")
        print()
        choice = input(BOLD("  → ")).strip().upper()

        if choice == "0":
            print(DIM("  Goodbye.\n"))
            break
        elif choice in ("1", "2", "3", "4"):
            names = ["easy", "medium", "hard", "veryhard"]
            name  = names[int(choice) - 1]
            solve_puzzle(name, PUZZLE_REGISTRY[name])
        elif choice == "5":
            run_all()
        elif choice == "6":
            file_path = input("  Enter file path: ").strip()
            p = Path(file_path)
            if p.exists():
                solve_puzzle(p.stem, p)
            else:
                print(RED(f"  File not found: {file_path}"))
        elif choice == "G":
            launch_gui()
        else:
            print(YELLOW("  Invalid choice, please try again."))
        print()


# ─────────────────────────────────────────────────────────────────────────────
#  GUI launcher
# ─────────────────────────────────────────────────────────────────────────────

def launch_gui():
    try:
        from game_gui import main as gui_main
        print(DIM("  Launching GUI..."))
        gui_main()
    except ImportError as e:
        print(RED(f"  GUI requires tkinter: {e}"))
        print(YELLOW("  Install with: pip install tk (or use system Python with tkinter)"))


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="CSP Sudoku Solver/Game — Backtracking + AC-3 + MRV + LCV"
    )
    parser.add_argument("--gui",    action="store_true",  help="Launch interactive GUI game")
    parser.add_argument("--all",    action="store_true",  help="Solve all four built-in puzzles")
    parser.add_argument("--puzzle", choices=["easy","medium","hard","veryhard"],
                        help="Solve a specific built-in puzzle")
    parser.add_argument("--file",   type=str,             help="Path to a custom puzzle file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.gui:
        launch_gui()
    elif args.all:
        run_all()
    elif args.puzzle:
        solve_puzzle(args.puzzle, PUZZLE_REGISTRY[args.puzzle])
    elif args.file:
        p = Path(args.file)
        solve_puzzle(p.stem, p)
    else:
        interactive_menu()

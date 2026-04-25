# 🧩 AI Sudoku Solver

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Algorithm](https://img.shields.io/badge/Algorithm-CSP%20%2B%20AC--3-6c8fff?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-All%204%20Solved-brightgreen?style=for-the-badge)

**A production-grade Sudoku solver built on Constraint Satisfaction Problem (CSP) theory.**  
Solves any valid 9×9 puzzle using Backtracking, AC-3 Arc Consistency, MRV, Degree Heuristic, and LCV — the same techniques used in real AI planning systems.

[🌐 Live Demo](https://ai-sudoku-solver-theta.vercel.app) • [📝 Medium Article](ADD_MEDIUM_LINK_HERE) • [⭐ Star this repo](#)

</div>

---

## 📸 Preview

```
        PUZZLE                      SOLUTION
+-------+-------+-------+    +-------+-------+-------+
| · · 3 | · 2 · | 6 · · |    | 4 8 3 | 9 2 1 | 6 5 7 |
| 9 · · | 3 · 5 | · · 1 |    | 9 6 7 | 3 4 5 | 8 2 1 |
| · · 1 | 8 · 6 | 4 · · |    | 2 5 1 | 8 7 6 | 4 9 3 |
+-------+-------+-------+    +-------+-------+-------+
| · · 8 | 1 · 2 | 9 · · |    | 5 4 8 | 1 3 2 | 9 7 6 |
| 7 · · | · · · | · · 8 |    | 7 2 9 | 5 6 4 | 1 3 8 |
| · · 6 | 7 · 8 | 2 · · |    | 1 3 6 | 7 9 8 | 2 4 5 |
+-------+-------+-------+    +-------+-------+-------+
| · · 2 | 6 · 9 | 5 · · |    | 3 7 2 | 6 8 9 | 5 1 4 |
| 8 · · | 2 · 3 | · · 9 |    | 8 1 4 | 2 5 3 | 7 6 9 |
| · · 5 | · 1 · | 3 · · |    | 6 9 5 | 4 1 7 | 3 8 2 |
+-------+-------+-------+    +-------+-------+-------+

✓ SOLVED  |  Time: 9 ms  |  Backtracks: 1  |  Failures: 0  |  Valid: YES
```

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🔁 **Backtracking Search** | Systematic depth-first search with intelligent pruning |
| ⚡ **AC-3 Arc Consistency** | Pre-processes all 810 arcs before search even begins |
| 🔍 **Forward Checking** | Eliminates values from peer domains on every assignment |
| 🎯 **MRV Heuristic** | Always picks the most-constrained cell next |
| 📐 **Degree Heuristic** | Tie-breaks MRV using the constraint graph |
| 🪶 **LCV Ordering** | Tries least-constraining values first to preserve options |
| 📊 **Performance Metrics** | Backtrack count, failure count, and solve time per puzzle |
| 🖥️ **CLI Interface** | Interactive menu + `--all`, `--puzzle`, and `--file` flags |
| ✅ **Solution Validator** | Verifies correctness of every solution automatically |

---

## 📊 Results

| Puzzle | Time | Backtracks | Failures | Status |
|--------|------|-----------|---------|--------|
| 🟢 Easy | 9 ms | 1 | 0 | ✅ Solved |
| 🟡 Medium | 1,917 ms | 777 | 1,078 | ✅ Solved |
| 🔴 Hard | 12,011 ms | 5,275 | 7,684 | ✅ Solved |
| ⚫ Very Hard *(AI Escargot)* | 658 ms | 330 | 365 | ✅ Solved |

> **Key insight:** The "Very Hard" AI Escargot puzzle solved faster than "Hard" with fewer backtracks.
> CSP difficulty and human-perceived difficulty are completely different axes.

---

## 🚀 Getting Started

**Requirements:** Python 3.11+ · No external dependencies

```bash
# 1. Clone the repository
git clone https://github.com/ZohaAshraf/ai-sudoku-solver.git
cd ai-sudoku-solver

# 2. Solve all four built-in puzzles
python main.py --all

# 3. Solve a specific difficulty
python main.py --puzzle hard

# 4. Load your own puzzle file
python main.py --file my_puzzle.txt

# 5. Interactive menu
python main.py
```

### Puzzle File Format

Nine lines of nine digits. `0` represents an empty cell.

```
003020600
900305001
001806400
008102900
700000008
006708200
002609500
800203009
005010300
```

---

## 🗂️ Project Structure

```
ai-sudoku-solver/
│
├── csp.py          # CSP engine — domains, AC-3, forward checking
├── solver.py       # Backtracking with MRV / Degree / LCV
├── io_utils.py     # File I/O, grid display, solution validation
├── main.py         # CLI interface
├── report.html     # Visual performance report (live on Vercel)
├── vercel.json     # Vercel deployment config
│
└── puzzles/
    ├── easy.txt
    ├── medium.txt
    ├── hard.txt
    └── veryhard.txt
```

---

## 🧠 How It Works

### 1 · CSP Formulation

The puzzle is modelled as a Constraint Satisfaction Problem:

- **Variables** — 81 cells `(row, col)`
- **Domains** — `{1..9}` for empty cells, `{digit}` for given cells
- **Constraints** — all-different across every row, column, and 3×3 box

### 2 · AC-3 Pre-processing

Before any search, AC-3 enforces arc consistency across all constraint pairs. For easy puzzles this alone resolves most cells — the solver finished Easy in just **9 ms with 1 backtrack call**.

### 3 · Backtracking Loop

```
while not solved:
    var   = MRV(unassigned) + Degree tiebreak
    for value in LCV(var):
        if consistent(var, value):
            assign(var, value)
            forward_check()   →  prune peers
            ac3()             →  propagate constraints
            recurse()
            if failed: unassign(var)   ← backtrack
```

### 4 · MRV + Degree

MRV picks the cell with the fewest remaining legal values — it fails fast and prunes the tree aggressively. When two cells tie, the Degree Heuristic selects the one with more unassigned neighbours to maximise propagation.

### 5 · LCV

Values are tried in ascending order of how many choices they eliminate from peer domains — keeping the search space open as long as possible.

---

## 🏗️ Architecture

The project is split into three clean, independent modules:

**`csp.py`** — pure CSP logic. Peer pre-computation, AC-3, forward checking. Zero solver code, zero I/O. Completely reusable for other CSP problems.

**`solver.py`** — backtracking engine. Calls `csp.py` for constraint operations and applies all three heuristics at each decision point. Returns a `SolveResult` with solution and stats.

**`io_utils.py`** — file parsing and display. Reads puzzle files, renders grids side-by-side, validates solutions.

---

## 📄 License

MIT — free to use, modify, and distribute.

---

<div align="center">

Made with ❤️ by [Zoha Ashraf](https://github.com/ZohaAshraf)  
If this helped you, consider giving it a ⭐

</div>

# 🧩 CSP Sudoku — Professional Solver & Playable Game

A full-featured Sudoku game and solver built on a Constraint Satisfaction Problem (CSP) engine with advanced AI heuristics.

---

## ✨ Features

### 🎮 Playable GUI Game (`game_gui.py`)
- **Interactive Tkinter interface** with dark theme
- **4 difficulty levels**: Easy, Medium, Hard, Very Hard
- **Real-time validation** — mistakes highlighted instantly in red
- **Hint system** powered by the CSP solver
- **Note mode** — pencil in candidate numbers (toggle with button)
- **Candidate display** — shows valid values for selected cell using AC-3
- **Auto-Solve** — instantly solve using the CSP engine
- **Animate Solve** — watch the solver work step-by-step
- **Live timer**, move counter, mistake counter
- **Cell highlighting**: selected cell, related row/col/box, same digit

### 🌐 Web Version (`sudoku_web.html`)
- Standalone, zero-dependency HTML file
- Full CSP solver ported to JavaScript
- Works in any browser — open directly or deploy to Vercel
- Same features: hints, animation, candidates, notes

### ⚙️ CLI Solver (`main.py`)
- Batch solve all puzzles with performance metrics
- Custom puzzle file loading
- GUI launcher from menu

---

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- `tkinter` (included with standard Python on Windows/macOS)

### Linux: Install tkinter if missing
```bash
# Ubuntu / Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

### Create Virtual Environment (VS Code)
```bash
# 1. Create venv
python -m venv .venv

# 2. Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install deps (none required, but for completeness)
pip install -r requirements.txt
```

### Select Interpreter in VS Code
1. Open Command Palette → `Python: Select Interpreter`
2. Choose `.venv/bin/python` (or `.venv\Scripts\python.exe`)

---

## 🚀 Running the Game

### GUI Game (recommended)
```bash
python game_gui.py
```

Or via main.py:
```bash
python main.py --gui
```

### Web Version
```bash
# Just open in browser:
open sudoku_web.html
# Or double-click the file
```

### CLI Solver
```bash
# Interactive menu (includes GUI option)
python main.py

# Solve specific difficulty
python main.py --puzzle hard

# Solve all puzzles with stats
python main.py --all

# Custom puzzle file
python main.py --file my_puzzle.txt
```

---

## 🎯 How to Play (GUI)

| Action          | Method                              |
|-----------------|-------------------------------------|
| Select cell     | Click on it                         |
| Enter number    | Click numpad or press 1-9 keys      |
| Erase cell      | Click ⌫ or press Backspace/Delete   |
| Navigate        | Arrow keys                          |
| Get hint        | Click 💡 Hint button                |
| Toggle notes    | Click ✎ Note Mode                   |
| Check progress  | Click ✔ Check                       |
| Auto-solve      | Click 🤖 Auto-Solve                 |
| Watch solver    | Click ▶ Animate Solve               |
| Reset puzzle    | Click ↺ Reset                       |
| New difficulty  | Click radio buttons on right panel  |

### Cell Colors
| Color        | Meaning                |
|--------------|------------------------|
| Dark navy    | Empty cell             |
| Darker navy  | Given/fixed digit      |
| Violet       | Selected cell          |
| Subtle blue  | Related cells (row/col/box) |
| Same shade   | Cells with same digit  |
| Red tint     | Incorrect entry        |
| Teal tint    | Hint-filled cell       |

### Digit Colors
| Color   | Meaning        |
|---------|----------------|
| White   | Given digit    |
| Violet  | Your entry     |
| Teal    | Hint digit     |
| Red     | Wrong entry    |

---

## 🧠 CSP Engine Architecture

```
csp.py          — Core constraint engine
├── SudokuCSP       Peer computation (row/col/box)
├── ac3()           Arc Consistency 3 (domain pruning)
├── forward_check() Remove value from peer domains
└── is_consistent() Binary constraint check

solver.py       — Search + heuristics
├── SudokuSolver    Main solver class
├── _backtrack()    Recursive search with pruning
├── _select_var()   MRV + Degree heuristic
└── _order_values() LCV value ordering

io_utils.py     — I/O and validation
game_gui.py     — Tkinter GUI game
sudoku_web.html — Self-contained browser version
main.py         — CLI entry point
```

### Algorithms Used

1. **AC-3 (Arc Consistency 3)** — Pre-processes the board, eliminating impossible values from domains using constraint propagation. O(ed³) complexity.

2. **MRV (Minimum Remaining Values)** — Always tries the cell with the fewest valid options first, dramatically cutting the search tree.

3. **Degree Heuristic** — Breaks MRV ties by choosing the cell with the most constraints on unfilled peers.

4. **LCV (Least Constraining Value)** — Orders value choices so the value that rules out the fewest options for neighbors comes first.

5. **Forward Checking** — After each assignment, propagates constraints to peers immediately.

6. **Backtracking** — Systematic search with constraint-guided pruning.

---

## 🌐 Deployment (Vercel)

### Option A: Web-Only (simplest)
Deploy `sudoku_web.html` directly — it's self-contained and runs entirely in the browser with no server needed.

```bash
# In Vercel dashboard: drag & drop sudoku_web.html
# OR use Vercel CLI:
npx vercel --prod
```

### Option B: Solver API (for backend use)
Create a `api/solve.py` file:
```python
from http.server import BaseHTTPRequestHandler
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from solver import SudokuSolver

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(length))
        solver = SudokuSolver(body['grid'])
        result = solver.solve()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'solution': result.solution,
            'stats': result.stats,
            'success': result.success
        }).encode())
```

Then call from your frontend:
```javascript
const res = await fetch('/api/solve', {
  method: 'POST',
  body: JSON.stringify({ grid: myGrid })
});
const { solution, stats } = await res.json();
```

---

## 📁 Project Structure

```
sudoku_game/
├── main.py              # CLI + GUI launcher
├── game_gui.py          # Tkinter game (dark theme)
├── sudoku_web.html      # Browser version (self-contained)
├── csp.py               # CSP engine (AC-3, peers, constraints)
├── solver.py            # Backtracking + MRV + LCV
├── io_utils.py          # File parsing + validation
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── puzzles/
    ├── easy.txt
    ├── medium.txt
    ├── hard.txt
    └── veryhard.txt     # AI Escargot — hardest known
```

---

## 📊 Performance Benchmarks

| Puzzle    | Time    | Backtracks | Notes              |
|-----------|---------|------------|--------------------|
| Easy      | ~1 ms   | ~10        | AC-3 solves most   |
| Medium    | ~5 ms   | ~50        | Light backtracking |
| Hard      | ~20 ms  | ~500       | MRV essential      |
| Very Hard | ~100 ms | ~5000      | AI Escargot puzzle |

*Results vary by hardware. MRV + AC-3 reduce naive search by 99%+.*

---

## 📝 Puzzle File Format

```
# Comments start with #
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

- 9 lines of 9 digits
- `0` = empty cell
- Whitespace between digits is optional

---

*Built with Python · Tkinter · CSP AI · Zero external dependencies*

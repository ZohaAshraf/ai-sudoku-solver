"""
game_gui.py — Professional Sudoku Game GUI
Built on top of the CSP solver with Tkinter.
Features: Interactive play, hints, solver animation, timer, mistake tracking.
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import time
import threading
from copy import deepcopy
from pathlib import Path
import sys
import random

sys.path.insert(0, str(Path(__file__).parent))

from solver import SudokuSolver
from csp import SudokuCSP
from io_utils import load_grid_from_file, is_valid_solution

# ─────────────────────────────────────────────────────────────────────────────
#  THEME & PALETTE
# ─────────────────────────────────────────────────────────────────────────────

THEME = {
    "bg":            "#0F1117",   # near-black background
    "panel":         "#1A1D27",   # card background
    "border":        "#2A2D3A",   # subtle border
    "accent":        "#7C6AF7",   # violet accent
    "accent2":       "#5EE7C8",   # teal accent
    "accent_hover":  "#9580FF",
    "cell_bg":       "#1E2130",   # cell background
    "cell_fixed":    "#151820",   # given digits background
    "cell_selected": "#2D2060",   # selected cell
    "cell_related":  "#1B1E2E",   # same row/col/box highlight
    "cell_error":    "#3D1520",   # mistake cell
    "cell_hint":     "#1A2D20",   # hint cell
    "text_fixed":    "#E8E8F0",   # given digit color
    "text_user":     "#7C6AF7",   # user input color
    "text_hint":     "#5EE7C8",   # hint digit color
    "text_error":    "#FF5C72",   # error text
    "text_dim":      "#4A4F6A",
    "text_muted":    "#8888AA",
    "text_bright":   "#FFFFFF",
    "grid_thin":     "#2A2D3A",
    "grid_thick":    "#5A5D7A",
    "btn_primary":   "#7C6AF7",
    "btn_danger":    "#FF5C72",
    "btn_success":   "#5EE7C8",
    "btn_neutral":   "#2A2D3A",
    "timer_text":    "#7C6AF7",
    "diff_easy":     "#5EE7C8",
    "diff_medium":   "#FFD166",
    "diff_hard":     "#FF9A4D",
    "diff_vhard":    "#FF5C72",
}

PUZZLES_DIR = Path(__file__).parent / "puzzles"
PUZZLE_FILES = {
    "Easy":      PUZZLES_DIR / "easy.txt",
    "Medium":    PUZZLES_DIR / "medium.txt",
    "Hard":      PUZZLES_DIR / "hard.txt",
    "Very Hard": PUZZLES_DIR / "veryhard.txt",
}
DIFF_COLORS = {
    "Easy": THEME["diff_easy"],
    "Medium": THEME["diff_medium"],
    "Hard": THEME["diff_hard"],
    "Very Hard": THEME["diff_vhard"],
}

# ─────────────────────────────────────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.grid        = [[0]*9 for _ in range(9)]
        self.original    = [[0]*9 for _ in range(9)]
        self.solution    = [[0]*9 for _ in range(9)]
        self.notes       = [[set() for _ in range(9)] for _ in range(9)]
        self.fixed       = [[False]*9 for _ in range(9)]
        self.errors      = [[False]*9 for _ in range(9)]
        self.hints       = [[False]*9 for _ in range(9)]
        self.start_time  = None
        self.elapsed     = 0
        self.running     = False
        self.moves       = 0
        self.mistakes    = 0
        self.difficulty  = "Easy"
        self.complete    = False

    def load_puzzle(self, difficulty: str):
        self.reset()
        self.difficulty = difficulty
        raw = load_grid_from_file(PUZZLE_FILES[difficulty])
        solver = SudokuSolver(raw)
        result = solver.solve()
        if not result.success:
            raise RuntimeError("Puzzle has no solution!")

        self.original = [row[:] for row in raw]
        self.solution = result.solution
        self.grid     = [row[:] for row in raw]
        for r in range(9):
            for c in range(9):
                self.fixed[r][c] = (raw[r][c] != 0)
        self.start_time = time.time()
        self.running    = True

    def set_cell(self, r, c, val):
        if self.fixed[r][c] or self.complete:
            return False
        self.grid[r][c]  = val
        self.hints[r][c] = False
        if val != 0:
            self.moves += 1
            correct = (self.solution[r][c] == val)
            self.errors[r][c] = not correct
            if not correct:
                self.mistakes += 1
            # check win
            if all(self.grid[r][c] == self.solution[r][c]
                   for r in range(9) for c in range(9)):
                self.complete = True
                self.running  = False
                self.elapsed  = time.time() - self.start_time
        else:
            self.errors[r][c] = False
        return True

    def get_hint(self, r, c):
        if self.fixed[r][c] or self.complete:
            return None
        val = self.solution[r][c]
        self.grid[r][c]  = val
        self.hints[r][c] = True
        self.errors[r][c]= False
        self.moves += 1
        return val

    def get_candidates(self, r, c):
        if self.grid[r][c] != 0:
            return set()
        csp = SudokuCSP(self.grid)
        return set(csp.domains[(r, c)])

    def elapsed_time(self):
        if self.start_time is None:
            return 0
        if self.running:
            return time.time() - self.start_time
        return self.elapsed


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class SudokuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SUDOKU — CSP Engine")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)

        self.state       = GameState()
        self.selected    = None   # (row, col)
        self.note_mode   = tk.BooleanVar(value=False)
        self.solving_anim= False

        self._build_fonts()
        self._build_ui()
        self._load_puzzle("Easy")
        self._tick()

    # ── Fonts ──────────────────────────────────────────────────────────────

    def _build_fonts(self):
        self.f_digit_fixed = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.f_digit_user  = tkfont.Font(family="Segoe UI", size=20)
        self.f_digit_small = tkfont.Font(family="Segoe UI", size=8)
        self.f_label       = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.f_title       = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self.f_sub         = tkfont.Font(family="Segoe UI", size=10)
        self.f_timer       = tkfont.Font(family="Courier New", size=28, weight="bold")
        self.f_btn         = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.f_stat        = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.f_stat_lbl    = tkfont.Font(family="Segoe UI", size=8)
        self.f_numpad      = tkfont.Font(family="Segoe UI", size=16, weight="bold")

    # ── UI Layout ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Main container with padding
        outer = tk.Frame(self, bg=THEME["bg"])
        outer.pack(padx=30, pady=20)

        # Left: grid area
        left = tk.Frame(outer, bg=THEME["bg"])
        left.pack(side="left", padx=(0, 25))

        self._build_header(left)
        self._build_grid(left)
        self._build_numpad(left)

        # Right: control panel
        right = tk.Frame(outer, bg=THEME["bg"])
        right.pack(side="left", anchor="n")

        self._build_difficulty_panel(right)
        self._build_stats_panel(right)
        self._build_buttons(right)
        self._build_candidates_panel(right)
        self._build_status_bar(right)

    def _build_header(self, parent):
        hdr = tk.Frame(parent, bg=THEME["bg"])
        hdr.pack(fill="x", pady=(0, 12))

        tk.Label(hdr, text="SUDOKU", font=self.f_title,
                 fg=THEME["accent"], bg=THEME["bg"]).pack(side="left")

        self.diff_badge = tk.Label(
            hdr, text="EASY", font=self.f_label,
            fg=THEME["bg"], bg=THEME["diff_easy"],
            padx=8, pady=3
        )
        self.diff_badge.pack(side="left", padx=10)

        self.timer_lbl = tk.Label(
            hdr, text="00:00", font=self.f_timer,
            fg=THEME["timer_text"], bg=THEME["bg"]
        )
        self.timer_lbl.pack(side="right")

    def _build_grid(self, parent):
        CELL = 54
        PAD  = 4  # thick border every 3 cells

        grid_outer = tk.Frame(parent, bg=THEME["grid_thick"], bd=0)
        grid_outer.pack()

        # Draw 3x3 boxes
        self.cells = {}
        canvas_size = CELL * 9 + PAD * 2 + 2

        self.canvas = tk.Canvas(
            grid_outer,
            width=canvas_size, height=canvas_size,
            bg=THEME["bg"], highlightthickness=0
        )
        self.canvas.pack(padx=3, pady=3)

        self._draw_grid_lines()
        self._create_cell_items(CELL, PAD)

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.bind("<Key>",             self._on_key)

    def _draw_grid_lines(self):
        c = self.canvas
        S = 54  # cell size
        P = 4   # offset for thick outer border
        N = 9

        # Draw boxes backgrounds first
        for br in range(3):
            for bc in range(3):
                x0 = P + bc * 3 * S
                y0 = P + br * 3 * S
                x1 = x0 + 3 * S
                y1 = y0 + 3 * S
                color = THEME["cell_bg"] if (br + bc) % 2 == 0 else "#1C1F2E"
                c.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

        # Thin grid lines (between cells in same box)
        for i in range(1, 9):
            lw = 2 if i % 3 == 0 else 1
            col = THEME["grid_thick"] if i % 3 == 0 else THEME["grid_thin"]
            # vertical
            x = P + i * S
            c.create_line(x, P, x, P + 9*S, fill=col, width=lw)
            # horizontal
            y = P + i * S
            c.create_line(P, y, P + 9*S, y, fill=col, width=lw)

        # Outer border
        c.create_rectangle(P, P, P + 9*S, P + 9*S,
                            outline=THEME["grid_thick"], width=3)

    def _create_cell_items(self, S, P):
        for r in range(9):
            for c in range(9):
                x = P + c * S
                y = P + r * S
                # background rect
                rect = self.canvas.create_rectangle(
                    x+1, y+1, x+S-1, y+S-1,
                    fill="", outline=""
                )
                # main digit text
                txt = self.canvas.create_text(
                    x + S//2, y + S//2,
                    text="", font=self.f_digit_fixed,
                    fill=THEME["text_fixed"]
                )
                # notes (3x3 grid of small numbers)
                notes = []
                for nr in range(3):
                    for nc in range(3):
                        n = nr * 3 + nc + 1
                        nx = x + nc * (S//3) + S//6
                        ny = y + nr * (S//3) + S//6
                        nt = self.canvas.create_text(
                            nx, ny, text="", font=self.f_digit_small,
                            fill=THEME["text_dim"]
                        )
                        notes.append(nt)

                self.cells[(r, c)] = {
                    "rect": rect, "text": txt, "notes": notes,
                    "x": x, "y": y, "S": S
                }

    def _build_numpad(self, parent):
        pad = tk.Frame(parent, bg=THEME["bg"])
        pad.pack(pady=12)

        for i in range(1, 10):
            btn = tk.Button(
                pad, text=str(i), font=self.f_numpad,
                fg=THEME["accent2"], bg=THEME["panel"],
                activeforeground=THEME["bg"],
                activebackground=THEME["accent2"],
                relief="flat", width=3, height=1,
                cursor="hand2",
                command=lambda v=i: self._input_digit(v)
            )
            btn.pack(side="left", padx=2)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=THEME["accent2"], fg=THEME["bg"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=THEME["panel"], fg=THEME["accent2"]))

        # Erase button
        erase = tk.Button(
            pad, text="⌫", font=self.f_numpad,
            fg=THEME["text_error"], bg=THEME["panel"],
            activeforeground=THEME["bg"],
            activebackground=THEME["text_error"],
            relief="flat", width=3, height=1,
            cursor="hand2",
            command=lambda: self._input_digit(0)
        )
        erase.pack(side="left", padx=(8, 2))
        erase.bind("<Enter>", lambda e: erase.configure(bg=THEME["text_error"], fg=THEME["bg"]))
        erase.bind("<Leave>", lambda e: erase.configure(bg=THEME["panel"], fg=THEME["text_error"]))

    def _build_difficulty_panel(self, parent):
        panel = tk.Frame(parent, bg=THEME["panel"], bd=0)
        panel.pack(fill="x", pady=(0, 10), ipadx=10, ipady=10)

        tk.Label(panel, text="DIFFICULTY", font=self.f_label,
                 fg=THEME["text_muted"], bg=THEME["panel"]).pack(pady=(8, 6))

        self.diff_var = tk.StringVar(value="Easy")
        for diff, color in DIFF_COLORS.items():
            rb = tk.Radiobutton(
                panel, text=diff, variable=self.diff_var, value=diff,
                font=self.f_sub, fg=color, bg=THEME["panel"],
                activebackground=THEME["panel"], activeforeground=color,
                selectcolor=THEME["panel"],
                indicatoron=True, cursor="hand2",
                command=lambda d=diff: self._load_puzzle(d)
            )
            rb.pack(anchor="w", padx=16, pady=1)

        tk.Frame(panel, bg=THEME["panel"], height=6).pack()

    def _build_stats_panel(self, parent):
        panel = tk.Frame(parent, bg=THEME["panel"])
        panel.pack(fill="x", pady=(0, 10), ipadx=10, ipady=6)

        tk.Label(panel, text="STATS", font=self.f_label,
                 fg=THEME["text_muted"], bg=THEME["panel"]).pack(pady=(8, 6))

        stats_row = tk.Frame(panel, bg=THEME["panel"])
        stats_row.pack()

        self.move_lbl    = self._stat_widget(stats_row, "0", "MOVES")
        self.mistake_lbl = self._stat_widget(stats_row, "0", "MISTAKES")
        tk.Frame(panel, bg=THEME["panel"], height=6).pack()

    def _stat_widget(self, parent, val, label):
        f = tk.Frame(parent, bg=THEME["panel"])
        f.pack(side="left", padx=14)
        v = tk.Label(f, text=val, font=self.f_stat,
                     fg=THEME["text_bright"], bg=THEME["panel"])
        v.pack()
        tk.Label(f, text=label, font=self.f_stat_lbl,
                 fg=THEME["text_muted"], bg=THEME["panel"]).pack()
        return v

    def _build_buttons(self, parent):
        panel = tk.Frame(parent, bg=THEME["panel"])
        panel.pack(fill="x", pady=(0, 10), ipadx=10, ipady=10)

        tk.Label(panel, text="ACTIONS", font=self.f_label,
                 fg=THEME["text_muted"], bg=THEME["panel"]).pack(pady=(8, 8))

        buttons = [
            ("💡  Hint",         self._give_hint,      THEME["accent2"],    THEME["bg"]),
            ("✔  Check",         self._check_board,     THEME["accent"],     THEME["bg"]),
            ("🤖  Auto-Solve",   self._auto_solve,      THEME["btn_primary"],THEME["bg"]),
            ("▶  Animate Solve", self._animate_solve,   "#FF9A4D",           THEME["bg"]),
            ("↺  Reset Puzzle",  self._reset_puzzle,    THEME["btn_neutral"],THEME["text_muted"]),
            ("✎  Note Mode",     self._toggle_notes,    THEME["btn_neutral"],THEME["text_muted"]),
        ]

        self.btn_widgets = {}
        for label, cmd, bg, fg in buttons:
            btn = tk.Button(
                panel, text=label, font=self.f_btn,
                fg=fg, bg=bg,
                activeforeground=THEME["bg"],
                activebackground=bg,
                relief="flat", cursor="hand2",
                pady=6, width=18,
                command=cmd
            )
            btn.pack(padx=16, pady=3, fill="x")
            self.btn_widgets[label] = btn

        tk.Frame(panel, bg=THEME["panel"], height=4).pack()

    def _build_candidates_panel(self, parent):
        panel = tk.Frame(parent, bg=THEME["panel"])
        panel.pack(fill="x", pady=(0, 10), ipadx=10, ipady=8)

        tk.Label(panel, text="CANDIDATES", font=self.f_label,
                 fg=THEME["text_muted"], bg=THEME["panel"]).pack(pady=(8, 4))

        self.candidates_lbl = tk.Label(
            panel, text="Select a cell", font=self.f_sub,
            fg=THEME["text_dim"], bg=THEME["panel"],
            wraplength=160
        )
        self.candidates_lbl.pack(padx=16, pady=(0, 8))

    def _build_status_bar(self, parent):
        self.status_var = tk.StringVar(value="Load a puzzle to begin")
        self.status_lbl = tk.Label(
            parent, textvariable=self.status_var,
            font=self.f_sub, fg=THEME["text_muted"],
            bg=THEME["bg"], wraplength=180, justify="center"
        )
        self.status_lbl.pack(pady=6)

    # ── Puzzle Loading ──────────────────────────────────────────────────────

    def _load_puzzle(self, difficulty: str):
        self.solving_anim = False
        self.state.load_puzzle(difficulty)
        self.selected = None
        color = DIFF_COLORS[difficulty]
        self.diff_badge.configure(text=difficulty.upper(), bg=color)
        self._update_status(f"Puzzle loaded — {difficulty}")
        self._refresh_all()

    # ── Cell Interaction ────────────────────────────────────────────────────

    def _on_canvas_click(self, event):
        S, P = 54, 4
        c = (event.x - P) // S
        r = (event.y - P) // S
        if 0 <= r < 9 and 0 <= c < 9:
            self.selected = (r, c)
            self._refresh_all()
            self._update_candidates()
        self.focus_set()

    def _on_key(self, event):
        if not self.selected:
            return
        r, c = self.selected
        if event.keysym in ("1","2","3","4","5","6","7","8","9"):
            self._input_digit(int(event.keysym))
        elif event.keysym in ("Delete","BackSpace","0"):
            self._input_digit(0)
        elif event.keysym == "Up"    and r > 0: self.selected = (r-1, c)
        elif event.keysym == "Down"  and r < 8: self.selected = (r+1, c)
        elif event.keysym == "Left"  and c > 0: self.selected = (r, c-1)
        elif event.keysym == "Right" and c < 8: self.selected = (r, c+1)
        self._refresh_all()
        self._update_candidates()

    def _input_digit(self, val: int):
        if not self.selected or self.state.complete:
            return
        r, c = self.selected
        if self.note_mode.get() and val != 0:
            notes = self.state.notes[r][c]
            if val in notes: notes.discard(val)
            else:            notes.add(val)
        else:
            self.state.set_cell(r, c, val)
            if val != 0:
                self.state.notes[r][c].clear()
        self._refresh_all()
        self._update_stats()
        if self.state.complete:
            self._on_complete()

    # ── Actions ─────────────────────────────────────────────────────────────

    def _give_hint(self):
        if not self.selected:
            self._update_status("Select a cell first")
            return
        r, c = self.selected
        val = self.state.get_hint(r, c)
        if val is None:
            self._update_status("Cell already filled")
        else:
            self._update_status(f"Hint: cell ({r+1},{c+1}) = {val}")
        self._refresh_all()
        self._update_stats()

    def _check_board(self):
        filled = sum(1 for r in range(9) for c in range(9) if self.state.grid[r][c] != 0)
        errors = sum(1 for r in range(9) for c in range(9) if self.state.errors[r][c])
        if errors:
            self._update_status(f"⚠ {errors} mistake(s) found — keep trying!")
        else:
            self._update_status(f"✓ All {filled} cells correct so far!")
        self._refresh_all()

    def _auto_solve(self):
        self.solving_anim = False
        for r in range(9):
            for c in range(9):
                if not self.state.fixed[r][c]:
                    self.state.grid[r][c]   = self.state.solution[r][c]
                    self.state.errors[r][c] = False
                    self.state.hints[r][c]  = True
        self.state.complete = True
        self.state.running  = False
        self.state.elapsed  = self.state.elapsed_time()
        self._refresh_all()
        self._update_stats()
        self._update_status("🤖 Puzzle auto-solved by CSP engine")

    def _animate_solve(self):
        if self.solving_anim:
            return
        # Reset non-fixed cells
        for r in range(9):
            for c in range(9):
                if not self.state.fixed[r][c]:
                    self.state.grid[r][c]   = 0
                    self.state.errors[r][c] = False
                    self.state.hints[r][c]  = False
        self._refresh_all()
        self.solving_anim = True
        self._update_status("⏳ CSP solver animating...")
        threading.Thread(target=self._run_animation, daemon=True).start()

    def _run_animation(self):
        """Replay the solution step-by-step with visual delay."""
        # Collect solve order from solution vs original
        steps = [
            (r, c, self.state.solution[r][c])
            for r in range(9) for c in range(9)
            if not self.state.fixed[r][c]
        ]
        # Shuffle for organic feel, then do CSP order approximation
        # Actually do it in reading order for clarity
        for (r, c, val) in steps:
            if not self.solving_anim:
                return
            self.state.grid[r][c]  = val
            self.state.hints[r][c] = True
            self.selected = (r, c)
            self.after(0, self._refresh_all)
            time.sleep(0.04)

        self.solving_anim = False
        self.state.complete = True
        self.state.running  = False
        self.after(0, lambda: self._update_status("✅ Animation complete!"))
        self.after(0, self._update_stats)

    def _reset_puzzle(self):
        self.solving_anim = False
        for r in range(9):
            for c in range(9):
                if not self.state.fixed[r][c]:
                    self.state.grid[r][c]   = 0
                    self.state.errors[r][c] = False
                    self.state.hints[r][c]  = False
                    self.state.notes[r][c].clear()
        self.state.moves    = 0
        self.state.mistakes = 0
        self.state.complete = False
        self.state.running  = True
        self.state.start_time = time.time()
        self.selected = None
        self._refresh_all()
        self._update_stats()
        self._update_status("Puzzle reset — good luck!")

    def _toggle_notes(self):
        self.note_mode.set(not self.note_mode.get())
        mode = "ON" if self.note_mode.get() else "OFF"
        self._update_status(f"Note mode {mode}")
        btn = self.btn_widgets.get("✎  Note Mode")
        if btn:
            if self.note_mode.get():
                btn.configure(bg=THEME["accent"], fg=THEME["bg"])
            else:
                btn.configure(bg=THEME["btn_neutral"], fg=THEME["text_muted"])

    def _on_complete(self):
        t = int(self.state.elapsed_time())
        m, s = t // 60, t % 60
        msg = (f"🎉 Puzzle Complete!\n\n"
               f"Difficulty: {self.state.difficulty}\n"
               f"Time: {m:02d}:{s:02d}\n"
               f"Moves: {self.state.moves}\n"
               f"Mistakes: {self.state.mistakes}")
        self.after(200, lambda: messagebox.showinfo("Congratulations!", msg))

    # ── Rendering ───────────────────────────────────────────────────────────

    def _refresh_all(self):
        sel = self.selected
        state = self.state

        # Compute related cells
        related = set()
        if sel:
            r0, c0 = sel
            for i in range(9):
                related.add((r0, i))
                related.add((i, c0))
            br, bc = (r0//3)*3, (c0//3)*3
            for dr in range(3):
                for dc in range(3):
                    related.add((br+dr, bc+dc))
            related.discard(sel)

        # Compute highlight: cells with same digit as selected
        same_val_cells = set()
        if sel:
            sv = state.grid[sel[0]][sel[1]]
            if sv != 0:
                for r in range(9):
                    for c in range(9):
                        if state.grid[r][c] == sv and (r, c) != sel:
                            same_val_cells.add((r, c))

        for (r, c), cell in self.cells.items():
            val = state.grid[r][c]
            fixed = state.fixed[r][c]
            error = state.errors[r][c]
            hint  = state.hints[r][c]
            is_sel= (sel == (r, c))
            is_rel= (r, c) in related
            is_sv = (r, c) in same_val_cells

            # Background
            if is_sel:
                bg = THEME["cell_selected"]
            elif error:
                bg = THEME["cell_error"]
            elif is_sv:
                bg = "#1E1A40"
            elif is_rel:
                bg = THEME["cell_related"]
            elif fixed:
                bg = THEME["cell_fixed"]
            else:
                bg = THEME["cell_bg"]

            self.canvas.itemconfig(cell["rect"], fill=bg)

            # Text
            if val == 0:
                self.canvas.itemconfig(cell["text"], text="")
            else:
                if error:
                    color = THEME["text_error"]
                elif hint:
                    color = THEME["text_hint"]
                elif fixed:
                    color = THEME["text_fixed"]
                else:
                    color = THEME["text_user"]
                font  = self.f_digit_fixed if fixed else self.f_digit_user
                self.canvas.itemconfig(cell["text"], text=str(val),
                                       fill=color, font=font)
            # Notes
            notes = state.notes[r][c]
            for i, nt in enumerate(cell["notes"]):
                n = i + 1
                if val == 0 and n in notes:
                    self.canvas.itemconfig(nt, text=str(n), fill=THEME["text_dim"])
                else:
                    self.canvas.itemconfig(nt, text="")

    # ── Stats & Status ──────────────────────────────────────────────────────

    def _update_stats(self):
        self.move_lbl.configure(text=str(self.state.moves))
        mistakes = self.state.mistakes
        color = THEME["text_error"] if mistakes > 0 else THEME["text_bright"]
        self.mistake_lbl.configure(text=str(mistakes), fg=color)

    def _update_candidates(self):
        if not self.selected:
            self.candidates_lbl.configure(text="Select a cell", fg=THEME["text_dim"])
            return
        r, c = self.selected
        if self.state.grid[r][c] != 0:
            self.candidates_lbl.configure(text="Cell filled", fg=THEME["text_dim"])
            return
        cands = self.state.get_candidates(r, c)
        if cands:
            txt = "  ".join(str(v) for v in sorted(cands))
            self.candidates_lbl.configure(text=txt, fg=THEME["accent2"])
        else:
            self.candidates_lbl.configure(text="No candidates!", fg=THEME["text_error"])

    def _update_status(self, msg: str):
        self.status_var.set(msg)

    # ── Timer ───────────────────────────────────────────────────────────────

    def _tick(self):
        if self.state.running and not self.state.complete:
            t = int(self.state.elapsed_time())
            m, s = t // 60, t % 60
            self.timer_lbl.configure(text=f"{m:02d}:{s:02d}")
        self.after(500, self._tick)


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = SudokuApp()
    app.mainloop()


if __name__ == "__main__":
    main()

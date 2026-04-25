"""
game_gui.py — Premium Sudoku Game (Pygame)
Ultra-polished UI with animations, sounds, lives system, scoring, combos.
"""

import pygame
import sys
import time
import math
import random
import os
from copy import deepcopy
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
from solver import SudokuSolver

# ── Constants ────────────────────────────────────────────────────────────────
W, H = 900, 700
FPS  = 60

PUZZLES = {
    "Easy":      BASE_DIR / "puzzles" / "easy.txt",
    "Medium":    BASE_DIR / "puzzles" / "medium.txt",
    "Hard":      BASE_DIR / "puzzles" / "hard.txt",
    "Very Hard": BASE_DIR / "puzzles" / "veryhard.txt",
}

# ── Palette ──────────────────────────────────────────────────────────────────
BG          = (12,  14,  22)
BG2         = (18,  21,  34)
PANEL_BG    = (22,  26,  42)
CELL_EMPTY  = (26,  30,  50)
CELL_FIXED  = (20,  24,  40)
CELL_SEL    = (80,  60, 180)
CELL_REL    = (32,  36,  58)
CELL_SAME   = (45,  40,  80)
CELL_ERR    = (180,  40,  55)
CELL_OK     = (30, 160, 110)
CELL_HINT   = (20, 130, 150)

TEXT_WHITE  = (230, 230, 245)
TEXT_FIXED  = (210, 210, 230)
TEXT_USER   = (160, 140, 255)
TEXT_ERR    = (255,  80,  90)
TEXT_OK     = ( 60, 220, 150)
TEXT_HINT   = ( 60, 200, 210)
TEXT_DIM    = ( 90,  90, 120)
TEXT_NOTE   = (120, 120, 160)

GOLD        = (255, 200,  50)
HEART_RED   = (220,  50,  80)
HEART_DEAD  = ( 70,  40,  50)
ACCENT      = (130, 100, 255)
ACCENT2     = ( 60, 200, 210)

LINE_THIN   = (45,  50,  80)
LINE_THICK  = (100, 100, 160)

# ── Load/parse puzzle ────────────────────────────────────────────────────────
def load_puzzle(path):
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
        raise ValueError(f"Bad puzzle: {path}")
    return grid

# ── Sound synthesis (no external files needed) ───────────────────────────────
def make_beep(freq=440, duration=0.08, volume=0.3, wave="sine", fade=True):
    try:
        import numpy as np
        sr = 22050
        n  = int(sr * duration)
        t  = np.linspace(0, duration, n, False)
        if wave == "sine":
            data = np.sin(2 * np.pi * freq * t)
        elif wave == "square":
            data = np.sign(np.sin(2 * np.pi * freq * t))
        else:
            data = np.sin(2 * np.pi * freq * t)
        if fade:
            env = np.linspace(1, 0, n) ** 0.5
            data *= env
        data = (data * volume * 32767).astype(np.int16)
        stereo = np.column_stack([data, data])
        return pygame.sndarray.make_sound(stereo)
    except Exception:
        return None

class SoundManager:
    def __init__(self):
        self.enabled = True
        self._sounds = {}
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._sounds["correct"] = make_beep(880, 0.07, 0.25, "sine")
            self._sounds["wrong"]   = make_beep(180, 0.18, 0.30, "square")
            self._sounds["hint"]    = make_beep(660, 0.12, 0.20, "sine")
            self._sounds["win"]     = self._make_fanfare()
            self._sounds["lose"]    = self._make_lose()
            self._sounds["select"]  = make_beep(500, 0.03, 0.08, "sine")
        except Exception:
            self.enabled = False

    def _make_fanfare(self):
        try:
            import numpy as np
            sr = 22050
            notes = [523, 659, 784, 1047]
            chunks = []
            for freq in notes:
                n = int(sr * 0.12)
                t = np.linspace(0, 0.12, n, False)
                d = np.sin(2*np.pi*freq*t) * np.linspace(1,0,n)**0.3
                chunks.append(d)
            data = np.concatenate(chunks)
            data = (data * 0.25 * 32767).astype(np.int16)
            stereo = np.column_stack([data, data])
            return pygame.sndarray.make_sound(stereo)
        except Exception:
            return None

    def _make_lose(self):
        try:
            import numpy as np
            sr = 22050
            notes = [300, 250, 200, 150]
            chunks = []
            for freq in notes:
                n = int(sr * 0.15)
                t = np.linspace(0, 0.15, n, False)
                d = np.sin(2*np.pi*freq*t) * np.linspace(1,0,n)**0.5
                chunks.append(d)
            data = np.concatenate(chunks)
            data = (data * 0.3 * 32767).astype(np.int16)
            stereo = np.column_stack([data, data])
            return pygame.sndarray.make_sound(stereo)
        except Exception:
            return None

    def play(self, name):
        if not self.enabled:
            return
        s = self._sounds.get(name)
        if s:
            try:
                s.play()
            except Exception:
                pass

# ── Particle system ───────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, vx=None, vy=None):
        self.x  = x
        self.y  = y
        self.vx = vx if vx is not None else random.uniform(-4, 4)
        self.vy = vy if vy is not None else random.uniform(-8, -2)
        self.color = color
        self.alpha = 255
        self.size  = random.randint(3, 8)
        self.life  = 1.0
        self.decay = random.uniform(0.015, 0.03)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.life -= self.decay
        self.alpha = int(self.life * 255)
        return self.life > 0

    def draw(self, surf):
        if self.alpha <= 0:
            return
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        col = (*self.color[:3], self.alpha)
        pygame.draw.circle(s, col, (self.size, self.size), self.size)
        surf.blit(s, (int(self.x - self.size), int(self.y - self.size)))

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, colors, n=20):
        for _ in range(n):
            c = random.choice(colors)
            self.particles.append(Particle(x, y, c))

    def confetti(self, rect):
        colors = [(ACCENT), ACCENT2, GOLD, (255,100,150), (100,255,180)]
        for _ in range(8):
            x = random.randint(rect.left, rect.right)
            y = random.randint(rect.top, rect.bottom)
            self.particles.append(Particle(x, y, random.choice(colors),
                                           random.uniform(-3,3), random.uniform(-6,-1)))

    def update_draw(self, surf):
        self.particles = [p for p in self.particles if p.update()]
        for p in self.particles:
            p.draw(surf)

# ── Animation helpers ─────────────────────────────────────────────────────────
def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return (2 ** (-10 * t)) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1

def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i]) * t) for i in range(3))

# ── Flash overlay ─────────────────────────────────────────────────────────────
class Flash:
    def __init__(self):
        self.items = []  # (r, c, color, start_t, duration)

    def add(self, r, c, color, duration=0.4):
        self.items.append([r, c, color, time.time(), duration])

    def get_alpha(self, r, c):
        now = time.time()
        best = 0
        best_col = None
        for item in self.items:
            ir, ic, col, st, dur = item
            if ir == r and ic == c:
                t = (now - st) / dur
                if t < 1.0:
                    a = int((1 - ease_out_cubic(t)) * 200)
                    if a > best:
                        best = a
                        best_col = col
        return best_col, best

    def clean(self):
        now = time.time()
        self.items = [i for i in self.items if (now - i[3]) < i[4]]

# ── Shake effect ──────────────────────────────────────────────────────────────
class Shake:
    def __init__(self):
        self.start = 0
        self.duration = 0
        self.magnitude = 0

    def trigger(self, magnitude=8, duration=0.35):
        self.start = time.time()
        self.duration = duration
        self.magnitude = magnitude

    def offset(self):
        t = time.time() - self.start
        if t >= self.duration:
            return 0, 0
        progress = t / self.duration
        decay = 1 - progress
        ox = math.sin(progress * math.pi * 8) * self.magnitude * decay
        oy = math.sin(progress * math.pi * 6) * self.magnitude * decay * 0.5
        return int(ox), int(oy)

# ── Pop animation (number placement) ─────────────────────────────────────────
class PopAnim:
    def __init__(self):
        self.items = {}  # (r,c) -> (start_t, scale_peak, color_flash)

    def trigger(self, r, c, ok=True):
        self.items[(r, c)] = (time.time(), 1.35 if ok else 1.0, ok)

    def get_scale(self, r, c):
        item = self.items.get((r, c))
        if not item:
            return 1.0
        st, peak, _ = item
        t = (time.time() - st) / 0.25
        if t >= 1.0:
            return 1.0
        return 1.0 + (peak - 1.0) * ease_out_elastic(1 - t)

# ── Floating score text ───────────────────────────────────────────────────────
class FloatText:
    def __init__(self):
        self.items = []  # (text, x, y, color, start_t)

    def add(self, text, x, y, color=TEXT_OK):
        self.items.append([text, x, y, color, time.time()])

    def update_draw(self, surf, font):
        now = time.time()
        alive = []
        for item in self.items:
            text, x, y, col, st = item
            t = now - st
            if t > 1.0:
                continue
            alpha = int((1 - t) * 255)
            dy = int(t * -50)
            s = font.render(text, True, col)
            s.set_alpha(alpha)
            surf.blit(s, (x - s.get_width()//2, y + dy))
            alive.append(item)
        self.items = alive

# ── Button ────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect, text, color=ACCENT, text_color=TEXT_WHITE, font=None, radius=10):
        self.rect       = pygame.Rect(rect)
        self.text       = text
        self.color      = color
        self.text_color = text_color
        self.font       = font
        self.radius     = radius
        self.hover      = False
        self.press_t    = 0

    def draw(self, surf):
        t = min(1.0, (time.time() - self.press_t) / 0.15)
        scale = 1.0 - 0.05 * (1 - t)
        col = self.color
        if self.hover:
            col = lerp_color(col, (255,255,255), 0.15)

        r = self.rect.inflate(
            int((scale-1)*self.rect.w), int((scale-1)*self.rect.h)
        )
        # Shadow
        shadow = r.move(2, 3)
        _draw_rounded_rect(surf, (0,0,0,80), shadow, self.radius, alpha=80)
        _draw_rounded_rect(surf, col, r, self.radius)

        if self.font:
            label = self.font.render(self.text, True, self.text_color)
            surf.blit(label, label.get_rect(center=r.center))

    def handle(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.press_t = time.time()
                return True
        return False

def _draw_rounded_rect(surf, color, rect, radius, alpha=255):
    if alpha < 255:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=radius)
        surf.blit(s, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)

# ── Main Game ─────────────────────────────────────────────────────────────────
class SudokuGame:
    BOARD_OFFSET = (50, 80)
    CELL_SIZE    = 62
    BOARD_SIZE   = CELL_SIZE * 9
    PANEL_X      = BOARD_OFFSET[0] + BOARD_SIZE + 24
    PANEL_W      = W - PANEL_X - 16

    MAX_LIVES    = 3
    MAX_HINTS    = 3

    DIFF_COLORS  = {
        "Easy":      (60, 200, 120),
        "Medium":    (255, 185,  50),
        "Hard":      (255,  90,  90),
        "Very Hard": (180,  80, 255),
    }

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("✦ Sudoku Premium")
        self.clock  = pygame.time.Clock()

        self._init_fonts()
        self.sounds  = SoundManager()
        self.flash   = Flash()
        self.shake   = Shake()
        self.pop     = PopAnim()
        self.floats  = FloatText()
        self.particles = ParticleSystem()

        self.difficulty  = "Easy"
        self.state       = "menu"   # menu | playing | gameover | win
        self._load_game(self.difficulty)

    # ── Font init ─────────────────────────────────────────────────────────────
    def _init_fonts(self):
        pygame.font.init()
        # Try to find a nice system font, fall back gracefully
        candidates = ["Consolas", "Courier New", "DejaVu Sans Mono", "monospace"]
        mono = pygame.font.match_font(" ".join(candidates)) or ""
        sans_candidates = ["Segoe UI", "Helvetica Neue", "Arial", "sans"]
        sans = pygame.font.match_font(" ".join(sans_candidates)) or ""

        self.font_huge   = pygame.font.Font(mono or None, 52)
        self.font_big    = pygame.font.Font(mono or None, 36)
        self.font_cell   = pygame.font.Font(sans or None, 34)
        self.font_note   = pygame.font.Font(sans or None, 11)
        self.font_ui     = pygame.font.Font(sans or None, 16)
        self.font_ui_sm  = pygame.font.Font(sans or None, 13)
        self.font_score  = pygame.font.Font(mono or None, 22)
        self.font_combo  = pygame.font.Font(mono or None, 28)
        self.font_title  = pygame.font.Font(mono or None, 48)
        self.font_sub    = pygame.font.Font(sans or None, 20)

    # ── Game load ─────────────────────────────────────────────────────────────
    def _load_game(self, difficulty):
        self.difficulty  = difficulty
        path = PUZZLES[difficulty]
        self.original    = load_puzzle(path)
        self.grid        = deepcopy(self.original)
        self.notes       = [[set() for _ in range(9)] for _ in range(9)]
        self.selected    = None
        self.note_mode   = False

        # Solve in background for hints/validation
        solver           = SudokuSolver(deepcopy(self.original))
        result           = solver.solve()
        self.solution    = result.solution if result.success else None

        self.lives       = self.MAX_LIVES
        self.hints_left  = self.MAX_HINTS
        self.score       = 0
        self.mistakes    = 0
        self.moves       = 0
        self.combo       = 0
        self.max_combo   = 0
        self.start_time  = time.time()
        self.elapsed     = 0
        self.paused      = False
        self.hint_cells  = set()
        self.animate_solve = False
        self.solve_steps = []
        self.solve_idx   = 0
        self.solve_timer = 0

        self._build_buttons()
        self.particles.particles.clear()
        self.flash.items.clear()
        self.pop.items.clear()

    def _build_buttons(self):
        px = self.PANEL_X
        pw = self.PANEL_W
        bh = 38
        bw = pw - 4
        bx = px + 2

        def btn(y, text, color=ACCENT, tc=TEXT_WHITE):
            return Button((bx, y, bw, bh), text, color, tc, self.font_ui, 10)

        self.btn_hint     = btn(300, "💡 Hint", (40,160,150))
        self.btn_note     = btn(348, "✎ Notes: OFF", (60,60,100))
        self.btn_solve    = btn(396, "🤖 Auto-Solve", (70,50,120))
        self.btn_animate  = btn(444, "▶ Watch Solve", (50,80,130))
        self.btn_new      = btn(520, "↺ New Game", (50,120,80))
        self.btn_menu     = btn(568, "⬅ Menu", (80,50,80))

        # Difficulty selector buttons
        diffs  = list(PUZZLES.keys())
        dw     = bw // 4 - 2
        self.diff_btns = []
        for i, d in enumerate(diffs):
            col = self.DIFF_COLORS[d]
            b   = Button((bx + i*(dw+2), 240, dw, 30), d[:1] if d!="Very Hard" else "VH",
                         col, TEXT_WHITE, self.font_ui_sm, 8)
            b._full = d
            self.diff_btns.append(b)

        # Numpad
        self.numpad_btns = []
        for i, n in enumerate(range(1, 10)):
            col = i % 3
            row = i // 3
            nx  = bx + col * (bw//3 + 1)
            ny  = 610 + row * 26
            b   = Button((nx, ny, bw//3 - 2, 22), str(n), (40,44,70), TEXT_USER, self.font_ui_sm, 6)
            self.numpad_btns.append(b)

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000
            self._handle_events()
            self._update(dt)
            self._draw()

    # ── Events ────────────────────────────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == "menu":
                self._menu_events(event)
            elif self.state == "playing":
                self._playing_events(event)
            elif self.state in ("gameover", "win"):
                self._endscreen_events(event)

    def _menu_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._load_game(self.difficulty)
            self.state = "playing"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Difficulty buttons
            for i, d in enumerate(PUZZLES.keys()):
                bw = (W - 200) // 4
                bx = 100 + i * (bw + 10)
                r  = pygame.Rect(bx, 380, bw, 52)
                if r.collidepoint(event.pos):
                    self.difficulty = d
            # Play button
            play_r = pygame.Rect(W//2 - 120, 480, 240, 56)
            if play_r.collidepoint(event.pos):
                self._load_game(self.difficulty)
                self.state = "playing"

    def _playing_events(self, event):
        # Animate-solve mode ignores input
        if self.animate_solve:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.animate_solve = False
            return

        if event.type == pygame.KEYDOWN:
            self._key_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_click(event.pos)

        # Button hover
        for btn in [self.btn_hint, self.btn_note, self.btn_solve,
                    self.btn_animate, self.btn_new, self.btn_menu]:
            btn.handle(event)
        for b in self.diff_btns + self.numpad_btns:
            b.handle(event)

    def _endscreen_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Restart
            r = pygame.Rect(W//2 - 120, H//2 + 100, 240, 50)
            if r.collidepoint(event.pos):
                self._load_game(self.difficulty)
                self.state = "playing"
            # Menu
            r2 = pygame.Rect(W//2 - 120, H//2 + 165, 240, 50)
            if r2.collidepoint(event.pos):
                self.state = "menu"
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._load_game(self.difficulty)
            self.state = "playing"

    def _key_event(self, event):
        k = event.key
        if k == pygame.K_ESCAPE:
            self.selected = None
        elif k in (pygame.K_n, pygame.K_TAB):
            self._toggle_notes()
        elif k == pygame.K_h:
            self._use_hint()
        elif k in (pygame.K_BACKSPACE, pygame.K_DELETE):
            self._erase()
        elif k in (pygame.K_1, pygame.K_KP1): self._enter_digit(1)
        elif k in (pygame.K_2, pygame.K_KP2): self._enter_digit(2)
        elif k in (pygame.K_3, pygame.K_KP3): self._enter_digit(3)
        elif k in (pygame.K_4, pygame.K_KP4): self._enter_digit(4)
        elif k in (pygame.K_5, pygame.K_KP5): self._enter_digit(5)
        elif k in (pygame.K_6, pygame.K_KP6): self._enter_digit(6)
        elif k in (pygame.K_7, pygame.K_KP7): self._enter_digit(7)
        elif k in (pygame.K_8, pygame.K_KP8): self._enter_digit(8)
        elif k in (pygame.K_9, pygame.K_KP9): self._enter_digit(9)
        elif k == pygame.K_UP    and self.selected: self.selected = (max(0,self.selected[0]-1), self.selected[1])
        elif k == pygame.K_DOWN  and self.selected: self.selected = (min(8,self.selected[0]+1), self.selected[1])
        elif k == pygame.K_LEFT  and self.selected: self.selected = (self.selected[0], max(0,self.selected[1]-1))
        elif k == pygame.K_RIGHT and self.selected: self.selected = (self.selected[0], min(8,self.selected[1]+1))

    def _mouse_click(self, pos):
        ox, oy = self.BOARD_OFFSET
        bx, by = pos

        # Board cell click
        cx = bx - ox
        cy = by - oy
        if 0 <= cx < self.BOARD_SIZE and 0 <= cy < self.BOARD_SIZE:
            c = cx // self.CELL_SIZE
            r = cy // self.CELL_SIZE
            if 0 <= r < 9 and 0 <= c < 9:
                self.selected = (r, c)
                self.sounds.play("select")
            return

        # Panel buttons
        if self.btn_hint.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
            self._use_hint()
        if self.btn_note.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
            self._toggle_notes()
        if self.btn_solve.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
            self._auto_solve()
        if self.btn_animate.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
            self._start_animate_solve()
        if self.btn_new.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
            self._load_game(self.difficulty)
        if self.btn_menu.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
            self.state = "menu"

        for b in self.diff_btns:
            if b.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
                self._load_game(b._full)

        for i, b in enumerate(self.numpad_btns):
            if b.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)):
                self._enter_digit(i+1)

    # ── Game actions ──────────────────────────────────────────────────────────
    def _enter_digit(self, digit):
        if self.lives <= 0 or self.state != "playing":
            return
        if not self.selected:
            return
        r, c = self.selected
        if self.original[r][c] != 0:
            return  # Fixed cell

        cx, cy = self._cell_center(r, c)

        if self.note_mode:
            if digit in self.notes[r][c]:
                self.notes[r][c].remove(digit)
            else:
                self.notes[r][c].add(digit)
            return

        self.grid[r][c] = digit
        self.notes[r][c].clear()
        self.moves += 1

        if self.solution and self.solution[r][c] != digit:
            # Wrong
            self.lives   -= 1
            self.mistakes+= 1
            self.combo    = 0
            self.score    = max(0, self.score - 50)
            self.flash.add(r, c, CELL_ERR, 0.6)
            self.pop.trigger(r, c, ok=False)
            self.shake.trigger()
            self.sounds.play("wrong")
            self.floats.add("-50", cx, cy, TEXT_ERR)
            self.particles.burst(cx, cy, [CELL_ERR, (255,120,120)], 12)

            if self.lives <= 0:
                pygame.time.delay(400)
                self.state = "gameover"
                self.sounds.play("lose")
        else:
            # Correct
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            bonus = 10 + (self.combo - 1) * 5
            time_bonus = max(0, 30 - int(self.elapsed // 60) * 5)
            pts = bonus + time_bonus
            self.score += pts
            self.flash.add(r, c, CELL_OK, 0.35)
            self.pop.trigger(r, c, ok=True)
            self.sounds.play("correct")
            label = f"+{pts}"
            if self.combo > 1:
                label += f" ×{self.combo}"
            self.floats.add(label, cx, cy, TEXT_OK)
            self.particles.burst(cx, cy, [CELL_OK, ACCENT2, (200,255,200)], 8)

            # Clear notes in peers
            self._clear_peer_notes(r, c, digit)

            if self._check_win():
                pygame.time.delay(200)
                self.state = "win"
                self.sounds.play("win")
                self._trigger_win_particles()

    def _clear_peer_notes(self, r, c, digit):
        # Clear note from row, col, box peers
        for cc in range(9):
            self.notes[r][cc].discard(digit)
        for rr in range(9):
            self.notes[rr][c].discard(digit)
        br, bc = (r//3)*3, (c//3)*3
        for dr in range(3):
            for dc in range(3):
                self.notes[br+dr][bc+dc].discard(digit)

    def _erase(self):
        if not self.selected:
            return
        r, c = self.selected
        if self.original[r][c] != 0:
            return
        self.grid[r][c] = 0
        self.notes[r][c].clear()

    def _toggle_notes(self):
        self.note_mode = not self.note_mode
        self.btn_note.text = f"✎ Notes: {'ON' if self.note_mode else 'OFF'}"
        self.btn_note.color = ACCENT2 if self.note_mode else (60,60,100)

    def _use_hint(self):
        if self.hints_left <= 0 or self.state != "playing":
            return
        hint = SudokuSolver(deepcopy(self.grid)).get_hint(self.grid)
        if not hint:
            return
        r, c, v = hint
        self.grid[r][c] = v
        self.notes[r][c].clear()
        self.hint_cells.add((r, c))
        self.hints_left -= 1
        self.score = max(0, self.score - 100)
        self.flash.add(r, c, CELL_HINT, 0.5)
        self.pop.trigger(r, c, ok=True)
        self.sounds.play("hint")
        cx, cy = self._cell_center(r, c)
        self.floats.add("Hint -100", cx, cy, TEXT_HINT)
        self._clear_peer_notes(r, c, v)
        if self._check_win():
            self.state = "win"
            self.sounds.play("win")
            self._trigger_win_particles()

    def _auto_solve(self):
        if self.solution:
            for r in range(9):
                for c in range(9):
                    self.grid[r][c] = self.solution[r][c]
            self.score = max(0, self.score - 500)
            self.state = "win"
            self.sounds.play("win")
            self._trigger_win_particles()

    def _start_animate_solve(self):
        if not self.solution:
            return
        self.animate_solve = True
        self.solve_steps   = []
        for r in range(9):
            for c in range(9):
                if self.original[r][c] == 0 and self.grid[r][c] == 0:
                    self.solve_steps.append((r, c, self.solution[r][c]))
        random.shuffle(self.solve_steps)  # Makes it look like it's "thinking"
        self.solve_steps.sort(key=lambda x: (x[0]//3*3+x[1]//3))  # Box order
        self.solve_idx  = 0
        self.solve_timer= 0

    def _check_win(self):
        for r in range(9):
            for c in range(9):
                if self.grid[r][c] == 0:
                    return False
                if self.solution and self.grid[r][c] != self.solution[r][c]:
                    return False
        return True

    def _trigger_win_particles(self):
        ox, oy = self.BOARD_OFFSET
        colors = [ACCENT, ACCENT2, GOLD, (255,100,150), TEXT_OK]
        for _ in range(60):
            x = random.randint(ox, ox + self.BOARD_SIZE)
            y = random.randint(oy, oy + self.BOARD_SIZE)
            self.particles.burst(x, y, colors, 3)

    # ── Update ────────────────────────────────────────────────────────────────
    def _update(self, dt):
        if self.state == "playing":
            self.elapsed = time.time() - self.start_time
            self.flash.clean()

            if self.animate_solve:
                self.solve_timer += dt
                delay = 0.06  # seconds per step
                while self.solve_timer >= delay and self.solve_idx < len(self.solve_steps):
                    r, c, v = self.solve_steps[self.solve_idx]
                    self.grid[r][c] = v
                    self.flash.add(r, c, CELL_HINT, 0.3)
                    self.pop.trigger(r, c, ok=True)
                    self.solve_idx  += 1
                    self.solve_timer -= delay
                if self.solve_idx >= len(self.solve_steps):
                    self.animate_solve = False
                    self.state = "win"
                    self.sounds.play("win")
                    self._trigger_win_particles()

        elif self.state == "win":
            # Periodic confetti
            ox, oy = self.BOARD_OFFSET
            if random.random() < 0.3:
                self.particles.confetti(pygame.Rect(ox, oy, self.BOARD_SIZE, self.BOARD_SIZE))

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        ox, oy = self.shake.offset()
        self.screen.fill(BG)
        self._draw_bg_decor()

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "playing":
            self._draw_game(ox, oy)
        elif self.state == "gameover":
            self._draw_game(0, 0)
            self._draw_gameover()
        elif self.state == "win":
            self._draw_game(0, 0)
            self._draw_win()

        self.particles.update_draw(self.screen)
        pygame.display.flip()

    def _draw_bg_decor(self):
        # Subtle grid pattern background
        for i in range(0, W, 60):
            pygame.draw.line(self.screen, (20, 23, 38), (i, 0), (i, H), 1)
        for i in range(0, H, 60):
            pygame.draw.line(self.screen, (20, 23, 38), (0, i), (W, i), 1)
        # Glow circles
        for cx, cy, r, col in [(150, 350, 200, (30,20,60)), (700, 200, 160, (20,40,60))]:
            s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, 60), (r, r), r)
            self.screen.blit(s, (cx-r, cy-r))

    # ── Menu ──────────────────────────────────────────────────────────────────
    def _draw_menu(self):
        # Title
        t1 = self.font_title.render("✦ SUDOKU", True, TEXT_WHITE)
        t2 = self.font_title.render("PREMIUM", True, ACCENT)
        self.screen.blit(t1, t1.get_rect(centerx=W//2, top=120))
        self.screen.blit(t2, t2.get_rect(centerx=W//2, top=175))

        sub = self.font_sub.render("AI-Powered · CSP Solver · MRV + AC-3 · Backtracking", True, TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(centerx=W//2, top=238))

        # Separator
        pygame.draw.line(self.screen, ACCENT, (W//2-180, 285), (W//2+180, 285), 1)

        diff_label = self.font_ui.render("SELECT DIFFICULTY", True, TEXT_DIM)
        self.screen.blit(diff_label, diff_label.get_rect(centerx=W//2, top=310))

        # Difficulty buttons
        diffs = list(PUZZLES.keys())
        total_w = len(diffs) * 160 + (len(diffs)-1)*14
        start_x = W//2 - total_w//2
        for i, d in enumerate(diffs):
            bx  = start_x + i * 174
            r   = pygame.Rect(bx, 340, 158, 70)
            col = self.DIFF_COLORS[d]
            sel = self.difficulty == d
            if sel:
                _draw_rounded_rect(self.screen, col, r, 12)
                pygame.draw.rect(self.screen, (255,255,255), r, 2, border_radius=12)
            else:
                _draw_rounded_rect(self.screen, (30,34,55), r, 12)
                pygame.draw.rect(self.screen, col, r, 2, border_radius=12)
            label_col = TEXT_WHITE if sel else col
            tl = self.font_ui.render(d, True, label_col)
            self.screen.blit(tl, tl.get_rect(centerx=r.centerx, centery=r.centery-8))
            if sel:
                dot = self.font_ui_sm.render("▶ SELECTED", True, (255,255,255,180))
                self.screen.blit(dot, dot.get_rect(centerx=r.centerx, centery=r.centery+12))

        # Play button
        play_r = pygame.Rect(W//2-130, 450, 260, 62)
        _draw_rounded_rect(self.screen, ACCENT, play_r, 14)
        tplay = self.font_big.render("▶  PLAY", True, TEXT_WHITE)
        self.screen.blit(tplay, tplay.get_rect(center=play_r.center))

        # Controls hint
        ctrl = self.font_ui_sm.render("Click a cell · 1-9 keys · Arrow keys to navigate", True, TEXT_DIM)
        self.screen.blit(ctrl, ctrl.get_rect(centerx=W//2, top=540))
        ctrl2 = self.font_ui_sm.render("H = Hint · N = Notes · Backspace = Erase", True, TEXT_DIM)
        self.screen.blit(ctrl2, ctrl2.get_rect(centerx=W//2, top=562))

    # ── Game ─────────────────────────────────────────────────────────────────
    def _draw_game(self, ox=0, oy=0):
        self._draw_header(ox, oy)
        self._draw_board(ox, oy)
        self._draw_panel()
        self.floats.update_draw(self.screen, self.font_score)

    def _draw_header(self, ox=0, oy=0):
        bx = self.BOARD_OFFSET[0] + ox
        # Title
        t = self.font_score.render(f"✦ SUDOKU PREMIUM  ·  {self.difficulty}", True, TEXT_DIM)
        self.screen.blit(t, (bx, 18 + oy))

        # Timer
        elapsed = int(self.elapsed)
        m, s = elapsed // 60, elapsed % 60
        timer_t = self.font_score.render(f"⏱ {m:02d}:{s:02d}", True,
                                          GOLD if elapsed < 120 else TEXT_WHITE)
        self.screen.blit(timer_t, (bx + 420, 18 + oy))

        # Hearts
        hx = bx + 250
        for i in range(self.MAX_LIVES):
            col = HEART_RED if i < self.lives else HEART_DEAD
            ht  = self.font_score.render("♥", True, col)
            self.screen.blit(ht, (hx + i * 30, 16 + oy))

        # Score
        sc_t = self.font_score.render(f"Score: {self.score:,}", True, ACCENT)
        self.screen.blit(sc_t, (bx, 48 + oy))

        # Combo
        if self.combo > 1:
            pulse = abs(math.sin(time.time() * 6)) * 0.4 + 0.6
            col   = tuple(int(c * pulse) for c in GOLD)
            ct    = self.font_combo.render(f"🔥 ×{self.combo} COMBO", True, col)
            self.screen.blit(ct, (bx + 240, 44 + oy))

        # Moves / Mistakes
        mt = self.font_ui.render(f"Moves: {self.moves}   Mistakes: {self.mistakes}", True, TEXT_DIM)
        self.screen.blit(mt, (bx + 430, 50 + oy))

    def _draw_board(self, ox=0, oy=0):
        bx = self.BOARD_OFFSET[0] + ox
        by = self.BOARD_OFFSET[1] + oy
        cs = self.CELL_SIZE

        sel = self.selected
        sel_val = self.grid[sel[0]][sel[1]] if sel else 0

        for r in range(9):
            for c in range(9):
                rx = bx + c * cs
                ry = by + r * cs
                rect = pygame.Rect(rx+1, ry+1, cs-2, cs-2)

                # Background color
                val      = self.grid[r][c]
                is_fixed = self.original[r][c] != 0
                is_hint  = (r, c) in self.hint_cells

                fl_col, fl_alpha = self.flash.get_alpha(r, c)

                if sel and (r, c) == sel:
                    base_col = CELL_SEL
                elif sel and (r == sel[0] or c == sel[1] or
                              (r//3 == sel[0]//3 and c//3 == sel[1]//3)):
                    base_col = CELL_REL
                elif sel_val and val == sel_val and val != 0:
                    base_col = CELL_SAME
                elif is_fixed:
                    base_col = CELL_FIXED
                else:
                    base_col = CELL_EMPTY

                if fl_col and fl_alpha > 0:
                    base_col = lerp_color(base_col, fl_col, fl_alpha / 200)

                pygame.draw.rect(self.screen, base_col, rect, border_radius=5)

                # Number
                if val != 0:
                    scale = self.pop.get_scale(r, c)
                    if is_hint:
                        ncol = TEXT_HINT
                    elif is_fixed:
                        ncol = TEXT_FIXED
                    else:
                        if self.solution and val != self.solution[r][c]:
                            ncol = TEXT_ERR
                        else:
                            ncol = TEXT_USER

                    if scale != 1.0:
                        fs = int(34 * scale)
                        fs = max(14, min(54, fs))
                        try:
                            f = pygame.font.Font(None, fs)
                        except Exception:
                            f = self.font_cell
                    else:
                        f = self.font_cell

                    nt = f.render(str(val), True, ncol)
                    cx2 = rx + cs // 2 - nt.get_width() // 2
                    cy2 = ry + cs // 2 - nt.get_height() // 2
                    self.screen.blit(nt, (cx2, cy2))

                elif self.notes[r][c] and not is_fixed:
                    # Draw small note numbers in 3x3 grid
                    nw = cs // 3
                    nh = cs // 3
                    for n in range(1, 10):
                        if n in self.notes[r][c]:
                            nr_ = (n-1) // 3
                            nc_ = (n-1) % 3
                            nx_ = rx + nc_ * nw + nw//2
                            ny_ = ry + nr_ * nh + nh//2
                            nt  = self.font_note.render(str(n), True, TEXT_NOTE)
                            self.screen.blit(nt, (nx_ - nt.get_width()//2, ny_ - nt.get_height()//2))

        # Draw grid lines
        for i in range(10):
            thick = 3 if i % 3 == 0 else 1
            col   = LINE_THICK if i % 3 == 0 else LINE_THIN
            # Vertical
            pygame.draw.line(self.screen, col,
                             (bx + i * cs, by),
                             (bx + i * cs, by + 9 * cs), thick)
            # Horizontal
            pygame.draw.line(self.screen, col,
                             (bx,          by + i * cs),
                             (bx + 9 * cs, by + i * cs), thick)

        # Outer border
        pygame.draw.rect(self.screen, ACCENT, (bx-1, by-1, 9*cs+2, 9*cs+2), 2, border_radius=4)

        # Animate-solve overlay
        if self.animate_solve:
            s = pygame.Surface((9*cs, 9*cs), pygame.SRCALPHA)
            s.fill((0, 0, 0, 40))
            self.screen.blit(s, (bx, by))
            txt = self.font_score.render("⚙ Solving... (ESC to stop)", True, ACCENT2)
            self.screen.blit(txt, txt.get_rect(centerx=bx+9*cs//2, centery=by-24))

    def _draw_panel(self):
        px = self.PANEL_X
        pw = self.PANEL_W
        # Panel background
        _draw_rounded_rect(self.screen, PANEL_BG, pygame.Rect(px-8, 72, pw+16, H-80), 12)

        # Section: Difficulty
        label = self.font_ui_sm.render("DIFFICULTY", True, TEXT_DIM)
        self.screen.blit(label, (px, 90))
        pygame.draw.line(self.screen, (50,55,90), (px, 106), (px+pw, 106), 1)

        # Diff color indicator
        col = self.DIFF_COLORS.get(self.difficulty, ACCENT)
        pygame.draw.circle(self.screen, col, (px+8, 120), 6)
        dt = self.font_ui.render(self.difficulty, True, col)
        self.screen.blit(dt, (px+20, 113))

        # Section: Stats
        label2 = self.font_ui_sm.render("STATS", True, TEXT_DIM)
        self.screen.blit(label2, (px, 148))
        pygame.draw.line(self.screen, (50,55,90), (px, 164), (px+pw, 164), 1)

        stats = [
            ("Score",    f"{self.score:,}",          ACCENT),
            ("Hints",    f"{self.hints_left}/{self.MAX_HINTS}", ACCENT2),
            ("Combo",    f"×{self.combo}" if self.combo > 1 else "—", GOLD),
            ("Max Combo",f"×{self.max_combo}",       TEXT_DIM),
        ]
        for i, (k, v, c) in enumerate(stats):
            ky = self.font_ui_sm.render(k, True, TEXT_DIM)
            vy = self.font_ui.render(v, True, c)
            self.screen.blit(ky, (px, 172 + i*18))
            self.screen.blit(vy, (px + pw - vy.get_width(), 172 + i*18))

        # Section: Controls
        label3 = self.font_ui_sm.render("CONTROLS", True, TEXT_DIM)
        self.screen.blit(label3, (px, 224))
        pygame.draw.line(self.screen, (50,55,90), (px, 240), (px+pw, 240), 1)

        for b in self.diff_btns:
            b.draw(self.screen)

        for btn in [self.btn_hint, self.btn_note, self.btn_solve, self.btn_animate,
                    self.btn_new, self.btn_menu]:
            btn.draw(self.screen)

        # Numpad label
        np_label = self.font_ui_sm.render("QUICK INPUT", True, TEXT_DIM)
        self.screen.blit(np_label, (px, 597))
        pygame.draw.line(self.screen, (50,55,90), (px, 608), (px+pw, 608), 1)
        for b in self.numpad_btns:
            b.draw(self.screen)

    # ── End screens ───────────────────────────────────────────────────────────
    def _draw_gameover(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((8, 5, 15, 200))
        self.screen.blit(overlay, (0, 0))

        # Shake the text
        sx, sy = self.shake.offset()

        t1 = self.font_huge.render("GAME OVER", True, HEART_RED)
        self.screen.blit(t1, t1.get_rect(centerx=W//2+sx, centery=H//2-80+sy))

        t2 = self.font_sub.render(f"You ran out of lives · Score: {self.score:,}", True, TEXT_DIM)
        self.screen.blit(t2, t2.get_rect(centerx=W//2, centery=H//2-20))

        _draw_rounded_rect(self.screen, (60,30,30), pygame.Rect(W//2-120, H//2+40, 240, 50), 12)
        tr = self.font_ui.render("↺  Try Again  (R)", True, TEXT_WHITE)
        self.screen.blit(tr, tr.get_rect(centerx=W//2, centery=H//2+65))

        _draw_rounded_rect(self.screen, (40,30,60), pygame.Rect(W//2-120, H//2+105, 240, 50), 12)
        tm = self.font_ui.render("⬅  Main Menu", True, TEXT_DIM)
        self.screen.blit(tm, tm.get_rect(centerx=W//2, centery=H//2+130))

    def _draw_win(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((5, 15, 10, 180))
        self.screen.blit(overlay, (0, 0))

        pulse = abs(math.sin(time.time() * 2)) * 0.2 + 0.8
        col   = tuple(int(c * pulse) for c in GOLD)

        t1 = self.font_huge.render("✦ SOLVED!", True, col)
        self.screen.blit(t1, t1.get_rect(centerx=W//2, centery=H//2-100))

        elapsed = int(self.elapsed)
        m, s    = elapsed // 60, elapsed % 60
        lines   = [
            (f"Final Score: {self.score:,}",        ACCENT),
            (f"Time: {m:02d}:{s:02d}",              TEXT_WHITE),
            (f"Mistakes: {self.mistakes}   Max Combo: ×{self.max_combo}", TEXT_DIM),
        ]
        for i, (line, c) in enumerate(lines):
            lt = self.font_sub.render(line, True, c)
            self.screen.blit(lt, lt.get_rect(centerx=W//2, centery=H//2-30+i*30))

        _draw_rounded_rect(self.screen, TEXT_OK, pygame.Rect(W//2-120, H//2+100, 240, 50), 12)
        tr = self.font_ui.render("↺  Play Again  (R)", True, BG)
        self.screen.blit(tr, tr.get_rect(centerx=W//2, centery=H//2+125))

        _draw_rounded_rect(self.screen, (40,30,60), pygame.Rect(W//2-120, H//2+165, 240, 50), 12)
        tm = self.font_ui.render("⬅  Main Menu", True, TEXT_DIM)
        self.screen.blit(tm, tm.get_rect(centerx=W//2, centery=H//2+190))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _cell_center(self, r, c):
        ox, oy = self.BOARD_OFFSET
        return (ox + c * self.CELL_SIZE + self.CELL_SIZE//2,
                oy + r * self.CELL_SIZE + self.CELL_SIZE//2)


def main():
    try:
        import numpy  # Optional, for better sounds
    except ImportError:
        pass
    game = SudokuGame()
    game.run()


if __name__ == "__main__":
    main()

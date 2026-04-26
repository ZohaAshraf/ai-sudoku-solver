"""
game_gui.py — Premium Sudoku Game (Pygame) — FIXED
Fixes: validation logic, hint system, performance, window decorations.
"""

import pygame
import sys
import time
import math
import random
from copy import deepcopy
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
from solver import SudokuSolver

W, H = 900, 700
FPS  = 60

PUZZLES = {
    "Easy":      BASE_DIR / "puzzles" / "easy.txt",
    "Medium":    BASE_DIR / "puzzles" / "medium.txt",
    "Hard":      BASE_DIR / "puzzles" / "hard.txt",
    "Very Hard": BASE_DIR / "puzzles" / "veryhard.txt",
}

# Palette
BG          = (12,  14,  22)
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


def _is_move_valid_csp(grid, r, c, digit):
    """Check digit doesn't conflict with row, col, box — ignoring the cell itself."""
    for cc in range(9):
        if cc != c and grid[r][cc] == digit:
            return False
    for rr in range(9):
        if rr != r and grid[rr][c] == digit:
            return False
    br, bc = (r // 3) * 3, (c // 3) * 3
    for dr in range(3):
        for dc in range(3):
            if (br+dr, bc+dc) != (r, c) and grid[br+dr][bc+dc] == digit:
                return False
    return True


# ── Sound ────────────────────────────────────────────────────────────────────
class SoundManager:
    def __init__(self):
        self.enabled = False
        self._sounds = {}
        try:
            import numpy as np
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self._sounds["correct"] = self._beep(880, 0.07, 0.25)
            self._sounds["wrong"]   = self._beep(180, 0.18, 0.30, "square")
            self._sounds["hint"]    = self._beep(660, 0.12, 0.20)
            self._sounds["select"]  = self._beep(500, 0.03, 0.08)
            self._sounds["win"]     = self._fanfare(np, [523, 659, 784, 1047])
            self._sounds["lose"]    = self._fanfare(np, [300, 250, 200, 150])
            self.enabled = True
        except Exception:
            pass

    def _beep(self, freq, dur, vol, wave="sine"):
        try:
            import numpy as np
            sr = 22050; n = int(sr*dur); t = np.linspace(0, dur, n, False)
            d = np.sin(2*np.pi*freq*t) if wave=="sine" else np.sign(np.sin(2*np.pi*freq*t))
            d *= np.linspace(1,0,n)**0.5 * vol
            s = (d * 32767).astype(np.int16)
            return pygame.sndarray.make_sound(np.column_stack([s, s]))
        except Exception:
            return None

    def _fanfare(self, np, notes):
        try:
            sr = 22050; chunks = []
            for freq in notes:
                n = int(sr*0.12); t = np.linspace(0, 0.12, n, False)
                d = np.sin(2*np.pi*freq*t) * np.linspace(1,0,n)**0.3
                chunks.append(d)
            data = np.concatenate(chunks)
            s = (data * 0.25 * 32767).astype(np.int16)
            return pygame.sndarray.make_sound(np.column_stack([s, s]))
        except Exception:
            return None

    def play(self, name):
        if not self.enabled: return
        s = self._sounds.get(name)
        if s:
            try: s.play()
            except Exception: pass


# ── Particles ─────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','vx','vy','color','alpha','size','life','decay')
    def __init__(self, x, y, color):
        self.x=x; self.y=y
        self.vx=random.uniform(-4,4); self.vy=random.uniform(-8,-2)
        self.color=color; self.alpha=255
        self.size=random.randint(3,7); self.life=1.0
        self.decay=random.uniform(0.018, 0.032)

    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=0.2
        self.life-=self.decay; self.alpha=int(self.life*255)
        return self.life > 0

    def draw(self, surf):
        if self.alpha<=0: return
        s=pygame.Surface((self.size*2,self.size*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.color[:3],self.alpha),(self.size,self.size),self.size)
        surf.blit(s,(int(self.x-self.size),int(self.y-self.size)))

class ParticleSystem:
    def __init__(self): self.particles=[]
    def burst(self, x, y, colors, n=16):
        for _ in range(n):
            self.particles.append(Particle(x,y,random.choice(colors)))
    def confetti(self, rect):
        cols=[ACCENT,ACCENT2,GOLD,(255,100,150),(100,255,180)]
        for _ in range(6):
            self.particles.append(Particle(
                random.randint(rect.left,rect.right),
                random.randint(rect.top,rect.bottom),
                random.choice(cols)))
    def update_draw(self, surf):
        self.particles=[p for p in self.particles if p.update()]
        for p in self.particles: p.draw(surf)


# ── Animation helpers ──────────────────────────────────────────────────────────
def ease_out_elastic(t):
    if t==0 or t==1: return t
    return (2**(-10*t))*math.sin((t*10-0.75)*(2*math.pi)/3)+1

def lerp_color(a, b, t):
    return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))


class Flash:
    def __init__(self): self.items=[]
    def add(self, r, c, color, duration=0.4):
        self.items.append([r,c,color,time.time(),duration])
    def get(self, r, c):
        now=time.time(); best=0; best_col=None
        for item in self.items:
            ir,ic,col,st,dur=item
            if ir==r and ic==c:
                t=(now-st)/dur
                if t<1.0:
                    a=int((1-(t**2))*200)
                    if a>best: best=a; best_col=col
        return best_col, best
    def clean(self):
        now=time.time()
        self.items=[i for i in self.items if (now-i[3])<i[4]]


class Shake:
    def __init__(self): self.start=0; self.dur=0; self.mag=0
    def trigger(self, mag=8, dur=0.35):
        self.start=time.time(); self.dur=dur; self.mag=mag
    def offset(self):
        t=time.time()-self.start
        if t>=self.dur: return 0,0
        p=t/self.dur; d=1-p
        return int(math.sin(p*math.pi*8)*self.mag*d), int(math.sin(p*math.pi*6)*self.mag*d*0.5)


class PopAnim:
    def __init__(self): self.items={}
    def trigger(self, r, c, ok=True):
        self.items[(r,c)]=(time.time(), 1.32 if ok else 1.0)
    def get_scale(self, r, c):
        item=self.items.get((r,c))
        if not item: return 1.0
        st,peak=item; t=(time.time()-st)/0.22
        if t>=1.0: return 1.0
        return 1.0+(peak-1.0)*ease_out_elastic(1-t)


class FloatText:
    def __init__(self): self.items=[]
    def add(self, text, x, y, color=TEXT_OK):
        self.items.append([text,x,y,color,time.time()])
    def update_draw(self, surf, font):
        now=time.time(); alive=[]
        for item in self.items:
            text,x,y,col,st=item; t=now-st
            if t>1.0: continue
            dy=int(t*-55); s=font.render(text,True,col)
            s.set_alpha(int((1-t)*255))
            surf.blit(s,(x-s.get_width()//2, y+dy))
            alive.append(item)
        self.items=alive


def _draw_rrect(surf, color, rect, radius, alpha=255):
    if alpha<255:
        s=pygame.Surface((rect.width,rect.height),pygame.SRCALPHA)
        pygame.draw.rect(s,(*color[:3],alpha),s.get_rect(),border_radius=radius)
        surf.blit(s,rect.topleft)
    else:
        pygame.draw.rect(surf,color,rect,border_radius=radius)


class Button:
    def __init__(self, rect, text, color=ACCENT, tc=TEXT_WHITE, font=None, r=10):
        self.rect=pygame.Rect(rect); self.text=text
        self.color=color; self.tc=tc; self.font=font; self.r=r
        self.hover=False; self.press_t=0

    def draw(self, surf):
        col=lerp_color(self.color,(255,255,255),0.15) if self.hover else self.color
        _draw_rrect(surf, col, self.rect, self.r)
        if self.font:
            lbl=self.font.render(self.text,True,self.tc)
            surf.blit(lbl,lbl.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if event.type==pygame.MOUSEMOTION:
            self.hover=self.rect.collidepoint(event.pos)
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if self.rect.collidepoint(event.pos):
                self.press_t=time.time(); return True
        return False

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


# ── Main Game ──────────────────────────────────────────────────────────────────
class SudokuGame:
    OX, OY   = 50, 80
    CS       = 62
    BS       = CS * 9
    PX       = OX + BS + 24
    PW       = W - PX - 16
    MAX_LIVES  = 3
    MAX_HINTS  = 3
    DIFF_COLORS = {
        "Easy":      (60, 200, 120),
        "Medium":    (255, 185,  50),
        "Hard":      (255,  90,  90),
        "Very Hard": (180,  80, 255),
    }

    def __init__(self):
        pygame.init()
        # Standard window — OS provides title bar, minimize, close
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Sudoku Premium")

        self.clock   = pygame.time.Clock()
        self._init_fonts()
        self._init_scaled_font_cache()

        self.sounds    = SoundManager()
        self.flash     = Flash()
        self.shake     = Shake()
        self.pop       = PopAnim()
        self.floats    = FloatText()
        self.particles = ParticleSystem()
        self._bg_surf  = None  # cached background

        self.difficulty = "Easy"
        self.state      = "menu"
        self._load_game("Easy")

    def _init_fonts(self):
        mono = pygame.font.match_font("Consolas,CourierNew,DejaVuSansMono") or None
        sans = pygame.font.match_font("SegoeUI,Arial,Helvetica") or None
        self.f_huge  = pygame.font.Font(mono, 52)
        self.f_big   = pygame.font.Font(mono, 36)
        self.f_cell  = pygame.font.Font(sans, 34)
        self.f_note  = pygame.font.Font(sans, 11)
        self.f_ui    = pygame.font.Font(sans, 16)
        self.f_sm    = pygame.font.Font(sans, 13)
        self.f_score = pygame.font.Font(mono, 22)
        self.f_combo = pygame.font.Font(mono, 28)
        self.f_title = pygame.font.Font(mono, 48)
        self.f_sub   = pygame.font.Font(sans, 20)

    def _init_scaled_font_cache(self):
        # Pre-cache scaled fonts for pop animation so we never create fonts mid-frame
        self._scale_fonts = {}
        sans = pygame.font.match_font("SegoeUI,Arial,Helvetica") or None
        for fs in range(14, 56, 2):
            self._scale_fonts[fs] = pygame.font.Font(sans, fs)

    def _get_scaled_font(self, size):
        # Round to nearest even
        s = max(14, min(54, int(size) // 2 * 2))
        return self._scale_fonts.get(s, self.f_cell)

    def _load_game(self, difficulty):
        self.difficulty = difficulty
        self.original   = load_puzzle(PUZZLES[difficulty])
        self.grid       = deepcopy(self.original)
        self.notes      = [[set() for _ in range(9)] for _ in range(9)]
        self.selected   = None
        self.note_mode  = False

        # ── FIX: solve from original ONCE, store solution, never re-solve during play
        result          = SudokuSolver(deepcopy(self.original)).solve()
        self.solution   = result.solution  # may be None if unsolvable (shouldn't happen)

        self.lives      = self.MAX_LIVES
        self.hints_left = self.MAX_HINTS
        self.score      = 0; self.mistakes = 0; self.moves = 0
        self.combo      = 0; self.max_combo = 0
        self.start_time = time.time(); self.elapsed = 0
        self.hint_cells = set()
        self.animate_solve = False
        self.solve_steps   = []; self.solve_idx = 0; self.solve_timer = 0

        self.flash.items.clear()
        self.pop.items.clear()
        self.particles.particles.clear()
        self._bg_surf = None  # invalidate cached bg
        self._build_buttons()

    def _build_buttons(self):
        px=self.PX; pw=self.PW; bw=pw-4; bx=px+2

        def btn(y, text, color=ACCENT, tc=TEXT_WHITE):
            return Button((bx,y,bw,38), text, color, tc, self.f_ui, 10)

        self.btn_hint    = btn(300, "Hint (H)", (40,160,150))
        self.btn_note    = btn(348, "Notes: OFF", (60,60,100))
        self.btn_solve   = btn(396, "Auto-Solve", (70,50,120))
        self.btn_animate = btn(444, "Watch Solve", (50,80,130))
        self.btn_new     = btn(520, "New Game", (50,120,80))
        self.btn_menu    = btn(568, "Back to Menu", (80,50,80))

        dw = bw//4 - 2
        self.diff_btns = []
        for i, d in enumerate(PUZZLES.keys()):
            col = self.DIFF_COLORS[d]
            label = d if len(d)<=6 else ("VH" if d=="Very Hard" else d[:4])
            b = Button((bx+i*(dw+2), 240, dw, 30), label, col, TEXT_WHITE, self.f_sm, 8)
            b._full = d
            self.diff_btns.append(b)

        self.numpad_btns = []
        for i in range(9):
            nc=i%3; nr=i//3
            b=Button((bx+nc*(bw//3+1), 610+nr*26, bw//3-2, 22),
                     str(i+1), (40,44,70), TEXT_USER, self.f_sm, 6)
            self.numpad_btns.append(b)

    # ── Run ───────────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000
            self._handle_events()
            self._update(dt)
            self._draw()

    # ── Events ────────────────────────────────────────────────────────────────
    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if self.state == "menu":
                self._ev_menu(ev)
            elif self.state == "playing":
                self._ev_playing(ev)
            elif self.state in ("gameover","win"):
                self._ev_end(ev)

    def _ev_menu(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
            self._load_game(self.difficulty); self.state="playing"
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button==1:
            diffs=list(PUZZLES.keys()); bw=(W-200)//4
            for i,d in enumerate(diffs):
                r=pygame.Rect(100+i*(bw+10), 340, bw, 70)
                if r.collidepoint(ev.pos): self.difficulty=d
            if pygame.Rect(W//2-130,450,260,62).collidepoint(ev.pos):
                self._load_game(self.difficulty); self.state="playing"

    def _ev_playing(self, ev):
        if self.animate_solve:
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE:
                self.animate_solve=False
            return

        # Pass to buttons first
        for btn in [self.btn_hint,self.btn_note,self.btn_solve,
                    self.btn_animate,self.btn_new,self.btn_menu]:
            btn.handle_event(ev)
        for b in self.diff_btns+self.numpad_btns:
            b.handle_event(ev)

        if ev.type == pygame.KEYDOWN:
            self._ev_key(ev)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button==1:
            self._ev_click(ev.pos)

    def _ev_end(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if pygame.Rect(W//2-120,H//2+100,240,50).collidepoint(ev.pos):
                self._load_game(self.difficulty); self.state="playing"
            if pygame.Rect(W//2-120,H//2+165,240,50).collidepoint(ev.pos):
                self.state="menu"
        if ev.type==pygame.KEYDOWN and ev.key==pygame.K_r:
            self._load_game(self.difficulty); self.state="playing"

    def _ev_key(self, ev):
        k=ev.key
        if   k==pygame.K_ESCAPE: self.selected=None
        elif k in (pygame.K_n,pygame.K_TAB): self._toggle_notes()
        elif k==pygame.K_h: self._use_hint()
        elif k in (pygame.K_BACKSPACE,pygame.K_DELETE): self._erase()
        elif k in (pygame.K_UP,pygame.K_KP8):
            if self.selected: self.selected=(max(0,self.selected[0]-1),self.selected[1])
        elif k in (pygame.K_DOWN,pygame.K_KP2):
            if self.selected: self.selected=(min(8,self.selected[0]+1),self.selected[1])
        elif k in (pygame.K_LEFT,pygame.K_KP4):
            if self.selected: self.selected=(self.selected[0],max(0,self.selected[1]-1))
        elif k in (pygame.K_RIGHT,pygame.K_KP6):
            if self.selected: self.selected=(self.selected[0],min(8,self.selected[1]+1))
        else:
            num = None
            if pygame.K_1<=k<=pygame.K_9: num=k-pygame.K_0
            elif pygame.K_KP1<=k<=pygame.K_KP9: num=k-pygame.K_KP0
            if num: self._enter_digit(num)

    def _ev_click(self, pos):
        cx=pos[0]-self.OX; cy=pos[1]-self.OY
        if 0<=cx<self.BS and 0<=cy<self.BS:
            c=cx//self.CS; r=cy//self.CS
            if 0<=r<9 and 0<=c<9:
                self.selected=(r,c); self.sounds.play("select")
            return

        if self.btn_hint.clicked(pos):    self._use_hint()
        if self.btn_note.clicked(pos):    self._toggle_notes()
        if self.btn_solve.clicked(pos):   self._auto_solve()
        if self.btn_animate.clicked(pos): self._start_animate()
        if self.btn_new.clicked(pos):     self._load_game(self.difficulty)
        if self.btn_menu.clicked(pos):    self.state="menu"

        for b in self.diff_btns:
            if b.clicked(pos): self._load_game(b._full)
        for i,b in enumerate(self.numpad_btns):
            if b.clicked(pos): self._enter_digit(i+1)

    # ── Game actions ──────────────────────────────────────────────────────────
    def _enter_digit(self, digit):
        if self.lives<=0 or self.state!="playing" or not self.selected: return
        r,c=self.selected
        if self.original[r][c]!=0: return   # fixed cell, ignore silently

        cx,cy=self._cell_center(r,c)

        if self.note_mode:
            self.notes[r][c].discard(digit) if digit in self.notes[r][c] else self.notes[r][c].add(digit)
            return

        self.grid[r][c]=digit
        self.notes[r][c].clear()
        self.moves+=1

        # ── FIX: validate against pre-computed solution (correct) ──────────
        # If no solution available, fall back to CSP constraint check
        if self.solution is not None:
            is_correct = (self.solution[r][c] == digit)
        else:
            # Fallback: basic constraint check (no duplicate in row/col/box)
            is_correct = _is_move_valid_csp(self.grid, r, c, digit)

        if not is_correct:
            self.lives-=1; self.mistakes+=1; self.combo=0
            self.score=max(0, self.score-50)
            self.flash.add(r,c,CELL_ERR,0.6)
            self.pop.trigger(r,c,ok=False)
            self.shake.trigger()
            self.sounds.play("wrong")
            self.floats.add("-50",cx,cy,TEXT_ERR)
            self.particles.burst(cx,cy,[CELL_ERR,(255,120,120)],12)
            if self.lives<=0:
                pygame.time.delay(300)
                self.state="gameover"; self.sounds.play("lose")
        else:
            self.combo+=1; self.max_combo=max(self.max_combo,self.combo)
            bonus=10+(self.combo-1)*5
            time_bonus=max(0,30-int(self.elapsed//60)*5)
            pts=bonus+time_bonus; self.score+=pts
            self.flash.add(r,c,CELL_OK,0.35)
            self.pop.trigger(r,c,ok=True)
            self.sounds.play("correct")
            lbl=f"+{pts}"+(f" x{self.combo}" if self.combo>1 else "")
            self.floats.add(lbl,cx,cy,TEXT_OK)
            self.particles.burst(cx,cy,[CELL_OK,ACCENT2,(200,255,200)],8)
            self._clear_peer_notes(r,c,digit)
            if self._check_win():
                pygame.time.delay(180)
                self.state="win"; self.sounds.play("win")
                self._win_particles()

    def _clear_peer_notes(self, r, c, digit):
        for cc in range(9): self.notes[r][cc].discard(digit)
        for rr in range(9): self.notes[rr][c].discard(digit)
        br,bc=(r//3)*3,(c//3)*3
        for dr in range(3):
            for dc in range(3): self.notes[br+dr][bc+dc].discard(digit)

    def _erase(self):
        if not self.selected: return
        r,c=self.selected
        if self.original[r][c]!=0: return
        self.grid[r][c]=0; self.notes[r][c].clear()

    def _toggle_notes(self):
        self.note_mode=not self.note_mode
        self.btn_note.text=f"Notes: {'ON' if self.note_mode else 'OFF'}"
        self.btn_note.color=ACCENT2 if self.note_mode else (60,60,100)

    def _use_hint(self):
        if self.hints_left<=0 or self.state!="playing" or not self.solution: return
        # ── FIX: use pre-computed solution directly, O(81) not O(solver)
        hint=None
        for r in range(9):
            for c in range(9):
                if self.grid[r][c]==0 and self.original[r][c]==0:
                    hint=(r,c,self.solution[r][c]); break
            if hint: break
        if not hint: return
        r,c,v=hint
        self.grid[r][c]=v; self.notes[r][c].clear()
        self.hint_cells.add((r,c)); self.hints_left-=1
        self.score=max(0,self.score-100)
        self.flash.add(r,c,CELL_HINT,0.5)
        self.pop.trigger(r,c,ok=True)
        self.sounds.play("hint")
        cx,cy=self._cell_center(r,c)
        self.floats.add("Hint -100",cx,cy,TEXT_HINT)
        self._clear_peer_notes(r,c,v)
        if self._check_win():
            self.state="win"; self.sounds.play("win"); self._win_particles()

    def _auto_solve(self):
        if not self.solution: return
        for r in range(9):
            for c in range(9): self.grid[r][c]=self.solution[r][c]
        self.score=max(0,self.score-500)
        self.state="win"; self.sounds.play("win"); self._win_particles()

    def _start_animate(self):
        if not self.solution: return
        self.animate_solve=True
        self.solve_steps=[(r,c,self.solution[r][c])
                          for r in range(9) for c in range(9)
                          if self.original[r][c]==0 and self.grid[r][c]==0]
        self.solve_steps.sort(key=lambda x:(x[0]//3*3+x[1]//3))
        self.solve_idx=0; self.solve_timer=0

    def _check_win(self):
        if not self.solution: return False
        for r in range(9):
            for c in range(9):
                if self.grid[r][c]!=self.solution[r][c]: return False
        return True

    def _win_particles(self):
        colors=[ACCENT,ACCENT2,GOLD,(255,100,150),TEXT_OK]
        for _ in range(50):
            x=random.randint(self.OX,self.OX+self.BS)
            y=random.randint(self.OY,self.OY+self.BS)
            self.particles.burst(x,y,colors,3)

    # ── Update ────────────────────────────────────────────────────────────────
    def _update(self, dt):
        if self.state=="playing":
            self.elapsed=time.time()-self.start_time
            self.flash.clean()
            if self.animate_solve:
                self.solve_timer+=dt
                while self.solve_timer>=0.06 and self.solve_idx<len(self.solve_steps):
                    r,c,v=self.solve_steps[self.solve_idx]
                    self.grid[r][c]=v
                    self.flash.add(r,c,CELL_HINT,0.3)
                    self.pop.trigger(r,c,ok=True)
                    self.solve_idx+=1; self.solve_timer-=0.06
                if self.solve_idx>=len(self.solve_steps):
                    self.animate_solve=False
                    self.state="win"; self.sounds.play("win"); self._win_particles()
        elif self.state=="win":
            if random.random()<0.2:
                self.particles.confetti(pygame.Rect(self.OX,self.OY,self.BS,self.BS))

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        ox,oy=self.shake.offset()
        self.screen.fill(BG)
        self._draw_bg()

        if self.state=="menu":
            self._draw_menu()
        elif self.state in ("playing","gameover","win"):
            self._draw_game(ox if self.state=="playing" else 0,
                            oy if self.state=="playing" else 0)
            if self.state=="gameover": self._draw_gameover()
            if self.state=="win":      self._draw_win()

        self.particles.update_draw(self.screen)
        pygame.display.flip()

    def _draw_bg(self):
        # Draw once into cached surface
        if self._bg_surf is None:
            self._bg_surf=pygame.Surface((W,H))
            self._bg_surf.fill(BG)
            for i in range(0,W,60):
                pygame.draw.line(self._bg_surf,(18,21,36),(i,0),(i,H),1)
            for i in range(0,H,60):
                pygame.draw.line(self._bg_surf,(18,21,36),(0,i),(W,i),1)
        self.screen.blit(self._bg_surf,(0,0))

    def _draw_menu(self):
        t1=self.f_title.render("SUDOKU PREMIUM",True,ACCENT)
        self.screen.blit(t1,t1.get_rect(centerx=W//2,top=110))
        sub=self.f_sm.render("AI-Powered  |  CSP Solver  |  Backtracking + AC-3 + MRV + LCV",True,TEXT_DIM)
        self.screen.blit(sub,sub.get_rect(centerx=W//2,top=180))
        pygame.draw.line(self.screen,ACCENT,(W//2-200,210),(W//2+200,210),1)

        dl=self.f_sm.render("SELECT DIFFICULTY",True,TEXT_DIM)
        self.screen.blit(dl,dl.get_rect(centerx=W//2,top=260))

        diffs=list(PUZZLES.keys()); bw=(W-200)//4
        for i,d in enumerate(diffs):
            bx=100+i*(bw+10); r=pygame.Rect(bx,300,bw,82)
            col=self.DIFF_COLORS[d]; sel=self.difficulty==d
            _draw_rrect(self.screen,col if sel else (30,34,55),r,12)
            pygame.draw.rect(self.screen,col,r,2,border_radius=12)
            lbl=self.f_ui.render(d,True,TEXT_WHITE if sel else col)
            self.screen.blit(lbl,lbl.get_rect(centerx=r.centerx,centery=r.centery))

        play=pygame.Rect(W//2-130,420,260,58)
        _draw_rrect(self.screen,ACCENT,play,14)
        pt=self.f_big.render("PLAY",True,TEXT_WHITE)
        self.screen.blit(pt,pt.get_rect(center=play.center))

        hints=[
            "Click a cell, then press 1-9 to enter a number",
            "H = Hint    N = Notes    Backspace = Erase    Arrow keys = Navigate",
        ]
        for i,h in enumerate(hints):
            ht=self.f_sm.render(h,True,TEXT_DIM)
            self.screen.blit(ht,ht.get_rect(centerx=W//2,top=510+i*22))

    def _draw_game(self, ox=0, oy=0):
        self._draw_header(ox,oy)
        self._draw_board(ox,oy)
        self._draw_panel()
        self.floats.update_draw(self.screen,self.f_score)

    def _draw_header(self, ox=0, oy=0):
        bx=self.OX+ox
        t=self.f_score.render(f"SUDOKU PREMIUM  |  {self.difficulty}",True,TEXT_DIM)
        self.screen.blit(t,(bx,18+oy))
        e=int(self.elapsed); m,s=e//60,e%60
        tc=GOLD if e<120 else TEXT_WHITE
        tt=self.f_score.render(f"{m:02d}:{s:02d}",True,tc)
        self.screen.blit(tt,(bx+430,18+oy))
        for i in range(self.MAX_LIVES):
            col=HEART_RED if i<self.lives else HEART_DEAD
            ht=self.f_score.render("v",True,col)  # use v as heart-ish
            ht=self.f_score.render(chr(9829),True,col)
            self.screen.blit(ht,(bx+260+i*30,16+oy))
        sc=self.f_score.render(f"Score: {self.score:,}",True,ACCENT)
        self.screen.blit(sc,(bx,46+oy))
        if self.combo>1:
            pulse=abs(math.sin(time.time()*5))*0.3+0.7
            col=tuple(int(c*pulse) for c in GOLD)
            ct=self.f_combo.render(f"x{self.combo} COMBO",True,col)
            self.screen.blit(ct,(bx+250,42+oy))
        mv=self.f_ui.render(f"Moves:{self.moves}  Mistakes:{self.mistakes}",True,TEXT_DIM)
        self.screen.blit(mv,(bx+430,50+oy))

    def _draw_board(self, ox=0, oy=0):
        bx=self.OX+ox; by=self.OY+oy; cs=self.CS
        sel=self.selected
        sel_val=self.grid[sel[0]][sel[1]] if sel else 0

        for r in range(9):
            for c in range(9):
                rx=bx+c*cs; ry=by+r*cs
                rect=pygame.Rect(rx+1,ry+1,cs-2,cs-2)
                val=self.grid[r][c]
                is_fixed=self.original[r][c]!=0
                is_hint=(r,c) in self.hint_cells
                fl_col,fl_alpha=self.flash.get(r,c)

                if sel and (r,c)==sel:          base=CELL_SEL
                elif sel and (r==sel[0] or c==sel[1] or
                              (r//3==sel[0]//3 and c//3==sel[1]//3)): base=CELL_REL
                elif sel_val and val==sel_val and val!=0: base=CELL_SAME
                elif is_fixed:                  base=CELL_FIXED
                else:                           base=CELL_EMPTY

                if fl_col and fl_alpha>0:
                    base=lerp_color(base,fl_col,fl_alpha/200)

                pygame.draw.rect(self.screen,base,rect,border_radius=5)

                if val!=0:
                    scale=self.pop.get_scale(r,c)
                    if is_hint:      ncol=TEXT_HINT
                    elif is_fixed:   ncol=TEXT_FIXED
                    elif self.solution and val!=self.solution[r][c]: ncol=TEXT_ERR
                    else:            ncol=TEXT_USER

                    if scale!=1.0:
                        f=self._get_scaled_font(34*scale)
                    else:
                        f=self.f_cell
                    nt=f.render(str(val),True,ncol)
                    self.screen.blit(nt,(rx+cs//2-nt.get_width()//2,
                                        ry+cs//2-nt.get_height()//2))
                elif self.notes[r][c] and not is_fixed:
                    nw=cs//3; nh=cs//3
                    for n in range(1,10):
                        if n in self.notes[r][c]:
                            nr_=(n-1)//3; nc_=(n-1)%3
                            nx_=rx+nc_*nw+nw//2; ny_=ry+nr_*nh+nh//2
                            nt=self.f_note.render(str(n),True,TEXT_NOTE)
                            self.screen.blit(nt,(nx_-nt.get_width()//2,ny_-nt.get_height()//2))

        # Grid lines
        for i in range(10):
            thick=3 if i%3==0 else 1; col=LINE_THICK if i%3==0 else LINE_THIN
            pygame.draw.line(self.screen,col,(bx+i*cs,by),(bx+i*cs,by+9*cs),thick)
            pygame.draw.line(self.screen,col,(bx,by+i*cs),(bx+9*cs,by+i*cs),thick)
        pygame.draw.rect(self.screen,ACCENT,(bx-1,by-1,9*cs+2,9*cs+2),2,border_radius=4)

        if self.animate_solve:
            ov=pygame.Surface((9*cs,9*cs),pygame.SRCALPHA)
            ov.fill((0,0,0,35)); self.screen.blit(ov,(bx,by))
            t=self.f_score.render("Solving... (ESC to stop)",True,ACCENT2)
            self.screen.blit(t,t.get_rect(centerx=bx+9*cs//2,centery=by-22))

    def _draw_panel(self):
        px=self.PX; pw=self.PW
        _draw_rrect(self.screen,PANEL_BG,pygame.Rect(px-8,72,pw+16,H-80),12)

        def label(text,y): 
            t=self.f_sm.render(text,True,TEXT_DIM)
            self.screen.blit(t,(px,y))
            pygame.draw.line(self.screen,(50,55,90),(px,y+16),(px+pw,y+16),1)

        label("DIFFICULTY",88)
        col=self.DIFF_COLORS.get(self.difficulty,ACCENT)
        dt=self.f_ui.render(self.difficulty,True,col)
        self.screen.blit(dt,(px+12,110))

        label("STATS",146)
        rows=[("Score",f"{self.score:,}",ACCENT),
              ("Hints left",f"{self.hints_left}/{self.MAX_HINTS}",ACCENT2),
              ("Combo",f"x{self.combo}" if self.combo>1 else "-",GOLD),
              ("Best combo",f"x{self.max_combo}",TEXT_DIM)]
        for i,(k,v,c) in enumerate(rows):
            ky=self.f_sm.render(k,True,TEXT_DIM)
            vy=self.f_ui.render(v,True,c)
            self.screen.blit(ky,(px,168+i*18))
            self.screen.blit(vy,(px+pw-vy.get_width(),168+i*18))

        label("DIFFICULTY SELECT",224)
        for b in self.diff_btns: b.draw(self.screen)

        label("ACTIONS",286)
        for b in [self.btn_hint,self.btn_note,self.btn_solve,
                  self.btn_animate,self.btn_new,self.btn_menu]:
            b.draw(self.screen)

        label("QUICK INPUT",596)
        for b in self.numpad_btns: b.draw(self.screen)

    def _draw_gameover(self):
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((8,5,15,195))
        self.screen.blit(ov,(0,0))
        t1=self.f_huge.render("GAME OVER",True,(220,50,80))
        self.screen.blit(t1,t1.get_rect(centerx=W//2,centery=H//2-80))
        t2=self.f_sub.render(f"You ran out of lives  |  Score: {self.score:,}",True,TEXT_DIM)
        self.screen.blit(t2,t2.get_rect(centerx=W//2,centery=H//2-20))
        _draw_rrect(self.screen,(70,30,30),pygame.Rect(W//2-120,H//2+40,240,50),12)
        tr=self.f_ui.render("Try Again  (R)",True,TEXT_WHITE)
        self.screen.blit(tr,tr.get_rect(centerx=W//2,centery=H//2+65))
        _draw_rrect(self.screen,(40,30,60),pygame.Rect(W//2-120,H//2+105,240,50),12)
        tm=self.f_ui.render("Main Menu",True,TEXT_DIM)
        self.screen.blit(tm,tm.get_rect(centerx=W//2,centery=H//2+130))

    def _draw_win(self):
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((5,15,10,175))
        self.screen.blit(ov,(0,0))
        pulse=abs(math.sin(time.time()*2))*0.2+0.8
        col=tuple(int(c*pulse) for c in GOLD)
        t1=self.f_huge.render("SOLVED!",True,col)
        self.screen.blit(t1,t1.get_rect(centerx=W//2,centery=H//2-100))
        e=int(self.elapsed); m,s=e//60,e%60
        for i,(line,c) in enumerate([
            (f"Score: {self.score:,}",ACCENT),
            (f"Time: {m:02d}:{s:02d}",TEXT_WHITE),
            (f"Mistakes: {self.mistakes}   Best Combo: x{self.max_combo}",TEXT_DIM)]):
            lt=self.f_sub.render(line,True,c)
            self.screen.blit(lt,lt.get_rect(centerx=W//2,centery=H//2-30+i*32))
        _draw_rrect(self.screen,TEXT_OK,pygame.Rect(W//2-120,H//2+100,240,50),12)
        tr=self.f_ui.render("Play Again  (R)",True,BG)
        self.screen.blit(tr,tr.get_rect(centerx=W//2,centery=H//2+125))
        _draw_rrect(self.screen,(40,30,60),pygame.Rect(W//2-120,H//2+165,240,50),12)
        tm=self.f_ui.render("Main Menu",True,TEXT_DIM)
        self.screen.blit(tm,tm.get_rect(centerx=W//2,centery=H//2+190))

    def _cell_center(self, r, c):
        return (self.OX+c*self.CS+self.CS//2, self.OY+r*self.CS+self.CS//2)


def main():
    game=SudokuGame(); game.run()

if __name__=="__main__":
    main()

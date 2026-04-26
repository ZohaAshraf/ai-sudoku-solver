"""
game_gui.py — Premium Sudoku Game (Pygame) — v3 FIXED UI
Fixes: header layout, hearts overlap, panel overlap, window close button, formatting.
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

# ── Window ────────────────────────────────────────────────────────────────────
W, H = 960, 720
FPS  = 60

PUZZLES = {
    "Easy":      BASE_DIR / "puzzles" / "easy.txt",
    "Medium":    BASE_DIR / "puzzles" / "medium.txt",
    "Hard":      BASE_DIR / "puzzles" / "hard.txt",
    "Very Hard": BASE_DIR / "puzzles" / "veryhard.txt",
}

# ── Palette ───────────────────────────────────────────────────────────────────
BG         = (13,  15,  24)
PANEL_BG   = (22,  26,  44)
CELL_EMPTY = (28,  32,  52)
CELL_FIXED = (20,  24,  40)
CELL_SEL   = (85,  65, 185)
CELL_REL   = (34,  38,  62)
CELL_SAME  = (50,  44,  88)
CELL_ERR   = (170,  36,  52)
CELL_OK    = (28, 155, 105)
CELL_HINT  = (18, 125, 145)
TXT_WHITE  = (232, 232, 248)
TXT_FIXED  = (200, 200, 225)
TXT_USER   = (165, 145, 255)
TXT_ERR    = (255,  85,  95)
TXT_OK     = ( 65, 225, 155)
TXT_HINT   = ( 65, 205, 215)
TXT_DIM    = ( 85,  88, 118)
TXT_NOTE   = (115, 115, 158)
GOLD       = (255, 200,  50)
HEART_ON   = (220,  55,  85)
HEART_OFF  = ( 65,  38,  50)
ACCENT     = (130, 100, 255)
ACCENT2    = ( 55, 195, 210)
LINE_THIN  = (42,  48,  78)
LINE_THICK = (95,  95, 158)


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


def csp_valid(grid, r, c, digit):
    """Check digit doesn't conflict with row/col/box (excluding cell itself)."""
    for cc in range(9):
        if cc != c and grid[r][cc] == digit: return False
    for rr in range(9):
        if rr != r and grid[rr][c] == digit: return False
    br, bc = (r//3)*3, (c//3)*3
    for dr in range(3):
        for dc in range(3):
            if (br+dr, bc+dc) != (r,c) and grid[br+dr][bc+dc] == digit: return False
    return True


# ── Sound ─────────────────────────────────────────────────────────────────────
class SoundManager:
    def __init__(self):
        self.ok = False
        self.s  = {}
        try:
            import numpy as np
            pygame.mixer.init(22050, -16, 2, 512)
            self.s["ok"]     = self._beep(np, 880, 0.07, 0.22)
            self.s["wrong"]  = self._beep(np, 180, 0.20, 0.28, sq=True)
            self.s["hint"]   = self._beep(np, 660, 0.12, 0.18)
            self.s["select"] = self._beep(np, 480, 0.03, 0.07)
            self.s["win"]    = self._fanfare(np, [523,659,784,1047])
            self.s["lose"]   = self._fanfare(np, [300,250,200,150])
            self.ok = True
        except Exception: pass

    def _beep(self, np, f, d, v, sq=False):
        try:
            sr=22050; n=int(sr*d); t=np.linspace(0,d,n,False)
            w=np.sign(np.sin(2*np.pi*f*t)) if sq else np.sin(2*np.pi*f*t)
            w=w*np.linspace(1,0,n)**0.5*v
            s=(w*32767).astype(np.int16)
            return pygame.sndarray.make_sound(np.column_stack([s,s]))
        except: return None

    def _fanfare(self, np, notes):
        try:
            sr=22050; chunks=[]
            for f in notes:
                n=int(sr*0.12); t=np.linspace(0,0.12,n,False)
                chunks.append(np.sin(2*np.pi*f*t)*np.linspace(1,0,n)**0.3)
            d=np.concatenate(chunks); s=(d*0.22*32767).astype(np.int16)
            return pygame.sndarray.make_sound(np.column_stack([s,s]))
        except: return None

    def play(self, name):
        if not self.ok: return
        snd=self.s.get(name)
        if snd:
            try: snd.play()
            except: pass


# ── Particles ─────────────────────────────────────────────────────────────────
class Particle:
    __slots__=('x','y','vx','vy','col','a','sz','life','dec')
    def __init__(self,x,y,col):
        self.x=x; self.y=y
        self.vx=random.uniform(-4,4); self.vy=random.uniform(-7,-1)
        self.col=col; self.a=255; self.sz=random.randint(3,7)
        self.life=1.0; self.dec=random.uniform(0.018,0.032)
    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=0.18
        self.life-=self.dec; self.a=int(self.life*255)
        return self.life>0
    def draw(self,surf):
        if self.a<=0: return
        s=pygame.Surface((self.sz*2,self.sz*2),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.col,self.a),(self.sz,self.sz),self.sz)
        surf.blit(s,(int(self.x-self.sz),int(self.y-self.sz)))

class Particles:
    def __init__(self): self.p=[]
    def burst(self,x,y,cols,n=14):
        for _ in range(n): self.p.append(Particle(x,y,random.choice(cols)))
    def confetti(self,rect):
        cols=[ACCENT,ACCENT2,GOLD,(255,100,150),(100,255,180)]
        for _ in range(5):
            self.p.append(Particle(random.randint(rect.left,rect.right),
                                   random.randint(rect.top,rect.bottom),random.choice(cols)))
    def update_draw(self,surf):
        self.p=[p for p in self.p if p.update()]
        for p in self.p: p.draw(surf)


# ── Anim helpers ──────────────────────────────────────────────────────────────
def ease_elastic(t):
    if t in (0,1): return t
    return (2**(-10*t))*math.sin((t*10-0.75)*(2*math.pi)/3)+1

def lc(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))


class Flash:
    def __init__(self): self.it=[]
    def add(self,r,c,col,dur=0.4): self.it.append([r,c,col,time.time(),dur])
    def get(self,r,c):
        now=time.time(); best=0; bc=None
        for item in self.it:
            ir,ic,col,st,dur=item
            if ir==r and ic==c:
                t=(now-st)/dur
                if t<1.0:
                    a=int((1-t**2)*200)
                    if a>best: best=a; bc=col
        return bc,best
    def clean(self): now=time.time(); self.it=[i for i in self.it if (now-i[3])<i[4]]


class Shake:
    def __init__(self): self.t0=0; self.d=0; self.m=0
    def go(self,m=8,d=0.35): self.t0=time.time(); self.d=d; self.m=m
    def off(self):
        t=time.time()-self.t0
        if t>=self.d: return 0,0
        p=t/self.d; decay=1-p
        return int(math.sin(p*math.pi*8)*self.m*decay), int(math.sin(p*math.pi*6)*self.m*decay*0.4)


class PopAnim:
    def __init__(self): self.it={}
    def go(self,r,c,ok=True): self.it[(r,c)]=(time.time(),1.30 if ok else 1.0)
    def scale(self,r,c):
        item=self.it.get((r,c))
        if not item: return 1.0
        st,pk=item; t=(time.time()-st)/0.22
        if t>=1.0: return 1.0
        return 1.0+(pk-1.0)*ease_elastic(1-t)


class FloatText:
    def __init__(self): self.it=[]
    def add(self,text,x,y,col=TXT_OK): self.it.append([text,x,y,col,time.time()])
    def draw(self,surf,font):
        now=time.time(); alive=[]
        for item in self.it:
            tx,x,y,col,st=item; t=now-st
            if t>1.0: continue
            dy=int(t*-52); s=font.render(tx,True,col)
            s.set_alpha(int((1-t)*255))
            surf.blit(s,(x-s.get_width()//2,y+dy))
            alive.append(item)
        self.it=alive


def rrect(surf,col,rect,r,alpha=255):
    if alpha<255:
        s=pygame.Surface((rect.width,rect.height),pygame.SRCALPHA)
        pygame.draw.rect(s,(*col[:3],alpha),s.get_rect(),border_radius=r)
        surf.blit(s,rect.topleft)
    else:
        pygame.draw.rect(surf,col,rect,border_radius=r)


class Btn:
    def __init__(self,rect,text,col=ACCENT,tc=TXT_WHITE,font=None,r=10):
        self.rect=pygame.Rect(rect); self.text=text
        self.col=col; self.tc=tc; self.font=font; self.r=r
        self.hover=False
    def draw(self,surf):
        c=lc(self.col,(255,255,255),0.12) if self.hover else self.col
        rrect(surf,c,self.rect,self.r)
        if self.font:
            lb=self.font.render(self.text,True,self.tc)
            surf.blit(lb,lb.get_rect(center=self.rect.center))
    def on_event(self,ev):
        if ev.type==pygame.MOUSEMOTION: self.hover=self.rect.collidepoint(ev.pos)
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            if self.rect.collidepoint(ev.pos): return True
        return False
    def hit(self,pos): return self.rect.collidepoint(pos)


# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    # Board geometry
    OX, OY = 44, 110   # board top-left
    CS = 64             # cell size
    BS = CS * 9         # board size = 576

    # Panel geometry  
    PX = OX + BS + 20  # panel left = 44+576+20 = 640
    PW = W - PX - 12   # panel width = 960-640-12 = 308

    MAX_LIVES = 3
    MAX_HINTS = 3

    DCOLS = {"Easy":(55,200,115),"Medium":(255,180,45),"Hard":(255,85,85),"Very Hard":(175,75,255)}

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Sudoku Premium")
        self.clock  = pygame.time.Clock()

        self._fonts()
        self._font_cache()
        self.snd   = SoundManager()
        self.flash = Flash()
        self.shake = Shake()
        self.pop   = PopAnim()
        self.ft    = FloatText()
        self.ptcl  = Particles()
        self._bgsurf = None

        self.diff  = "Easy"
        self.state = "menu"
        self._new("Easy")

    def _fonts(self):
        mono = pygame.font.match_font("Consolas,CourierNew,DejaVuSansMono") or None
        sans = pygame.font.match_font("SegoeUI,Arial,Ubuntu,FreeSans") or None
        self.fHuge  = pygame.font.Font(mono, 54)
        self.fBig   = pygame.font.Font(mono, 38)
        self.fCell  = pygame.font.Font(sans, 36)
        self.fNote  = pygame.font.Font(sans, 11)
        self.fUI    = pygame.font.Font(sans, 17)
        self.fSM    = pygame.font.Font(sans, 13)
        self.fScore = pygame.font.Font(mono, 20)
        self.fCombo = pygame.font.Font(mono, 26)
        self.fTitle = pygame.font.Font(mono, 50)
        self.fSub   = pygame.font.Font(sans, 18)
        self.fHeart = pygame.font.Font(sans, 22)  # dedicated heart font

    def _font_cache(self):
        sans = pygame.font.match_font("SegoeUI,Arial,Ubuntu,FreeSans") or None
        self._sf = {sz: pygame.font.Font(sans, sz) for sz in range(14, 56, 2)}

    def _sf_get(self, sz):
        s = max(14, min(54, int(sz)//2*2))
        return self._sf.get(s, self.fCell)

    def _new(self, diff):
        self.diff   = diff
        self.orig   = load_puzzle(PUZZLES[diff])
        self.grid   = deepcopy(self.orig)
        self.notes  = [[set() for _ in range(9)] for _ in range(9)]
        self.sel    = None
        self.nmode  = False

        res = SudokuSolver(deepcopy(self.orig)).solve()
        self.sol    = res.solution   # None only if puzzle broken

        self.lives  = self.MAX_LIVES
        self.hints  = self.MAX_HINTS
        self.score  = 0; self.err = 0; self.moves = 0
        self.combo  = 0; self.maxc = 0
        self.t0     = time.time(); self.elapsed = 0
        self.hcells = set()
        self.anim   = False; self.asteps=[]; self.aidx=0; self.atimer=0

        self.flash.it.clear(); self.pop.it.clear(); self.ptcl.p.clear()
        self._bgsurf = None
        self._btns()

    def _btns(self):
        px=self.PX; pw=self.PW; bw=pw; bx=px
        bh=40

        def B(y,text,col=ACCENT,tc=TXT_WHITE):
            return Btn((bx,y,bw,bh),text,col,tc,self.fUI,10)

        # Actions start lower so stats section has room
        self.bHint   = B(390, "Hint  (H)",     (35,155,145))
        self.bNote   = B(438, "Notes: OFF",     (55,55,100))
        self.bSolve  = B(486, "Auto-Solve",     (65,45,115))
        self.bAnim   = B(534, "Watch Solve",    (45,75,125))
        self.bNew    = B(610, "New Game",       (45,115,75))
        self.bMenu   = B(658, "Back to Menu",   (75,45,75))

        # Difficulty row
        dw = (bw-6)//4
        self.dBtns=[]
        for i,d in enumerate(PUZZLES):
            col=self.DCOLS[d]
            label={"Easy":"Easy","Medium":"Med","Hard":"Hard","Very Hard":"VH"}[d]
            b=Btn((bx+i*(dw+2),330,dw,32),label,col,TXT_WHITE,self.fSM,8)
            b._full=d; self.dBtns.append(b)

        # Numpad 3x3
        nw=(bw-4)//3
        self.nBtns=[]
        for i in range(9):
            nc=i%3; nr=i//3
            b=Btn((bx+nc*(nw+2),712+nr*28,nw,24),str(i+1),(38,42,68),TXT_USER,self.fSM,6)
            # push below screen — numpad is available via keyboard only for now
            self.nBtns.append(b)

    # ── Loop ──────────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt=self.clock.tick(FPS)/1000
            self._events()
            self._update(dt)
            self._draw()

    # ── Events ────────────────────────────────────────────────────────────────
    def _events(self):
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: pygame.quit(); sys.exit()

            if self.state=="menu":
                self._ev_menu(ev)
            elif self.state=="playing":
                self._ev_play(ev)
            elif self.state in ("win","over"):
                self._ev_end(ev)

    def _ev_menu(self,ev):
        if ev.type==pygame.KEYDOWN and ev.key==pygame.K_RETURN:
            self._new(self.diff); self.state="playing"
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            diffs=list(PUZZLES); bw=(W-200)//4
            for i,d in enumerate(diffs):
                if pygame.Rect(100+i*(bw+10),310,bw,80).collidepoint(ev.pos):
                    self.diff=d
            if pygame.Rect(W//2-130,430,260,60).collidepoint(ev.pos):
                self._new(self.diff); self.state="playing"

    def _ev_play(self,ev):
        if self.anim:
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: self.anim=False
            return

        for b in [self.bHint,self.bNote,self.bSolve,self.bAnim,self.bNew,self.bMenu]:
            b.on_event(ev)
        for b in self.dBtns: b.on_event(ev)

        if ev.type==pygame.KEYDOWN: self._ev_key(ev)
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1: self._ev_click(ev.pos)

    def _ev_end(self,ev):
        if ev.type==pygame.MOUSEBUTTONDOWN:
            if pygame.Rect(W//2-120,H//2+90,240,50).collidepoint(ev.pos):
                self._new(self.diff); self.state="playing"
            if pygame.Rect(W//2-120,H//2+152,240,50).collidepoint(ev.pos):
                self.state="menu"
        if ev.type==pygame.KEYDOWN and ev.key==pygame.K_r:
            self._new(self.diff); self.state="playing"

    def _ev_key(self,ev):
        k=ev.key
        if   k==pygame.K_ESCAPE: self.sel=None
        elif k in(pygame.K_n,pygame.K_TAB): self._toggle_notes()
        elif k==pygame.K_h: self._hint()
        elif k in(pygame.K_BACKSPACE,pygame.K_DELETE): self._erase()
        elif k in(pygame.K_UP,pygame.K_KP8):
            if self.sel: self.sel=(max(0,self.sel[0]-1),self.sel[1])
        elif k in(pygame.K_DOWN,pygame.K_KP2):
            if self.sel: self.sel=(min(8,self.sel[0]+1),self.sel[1])
        elif k in(pygame.K_LEFT,pygame.K_KP4):
            if self.sel: self.sel=(self.sel[0],max(0,self.sel[1]-1))
        elif k in(pygame.K_RIGHT,pygame.K_KP6):
            if self.sel: self.sel=(self.sel[0],min(8,self.sel[1]+1))
        else:
            n=None
            if pygame.K_1<=k<=pygame.K_9: n=k-pygame.K_0
            elif pygame.K_KP1<=k<=pygame.K_KP9: n=k-pygame.K_KP0
            if n: self._digit(n)

    def _ev_click(self,pos):
        # Board
        cx=pos[0]-self.OX; cy=pos[1]-self.OY
        if 0<=cx<self.BS and 0<=cy<self.BS:
            c=cx//self.CS; r=cy//self.CS
            if 0<=r<9 and 0<=c<9:
                self.sel=(r,c); self.snd.play("select")
            return
        # Buttons
        if self.bHint.hit(pos):  self._hint()
        if self.bNote.hit(pos):  self._toggle_notes()
        if self.bSolve.hit(pos): self._autosolve()
        if self.bAnim.hit(pos):  self._start_anim()
        if self.bNew.hit(pos):   self._new(self.diff)
        if self.bMenu.hit(pos):  self.state="menu"
        for b in self.dBtns:
            if b.hit(pos): self._new(b._full)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _digit(self, digit):
        if self.lives<=0 or self.state!="playing" or not self.sel: return
        r,c=self.sel
        if self.orig[r][c]!=0: return  # fixed

        cx,cy=self._cc(r,c)

        if self.nmode:
            if digit in self.notes[r][c]: self.notes[r][c].discard(digit)
            else: self.notes[r][c].add(digit)
            return

        self.grid[r][c]=digit
        self.notes[r][c].clear()
        self.moves+=1

        # Validate against solution (primary) or CSP fallback
        if self.sol is not None:
            correct = (self.sol[r][c] == digit)
        else:
            correct = csp_valid(self.grid, r, c, digit)

        if not correct:
            self.lives-=1; self.err+=1; self.combo=0
            self.score=max(0,self.score-50)
            self.flash.add(r,c,CELL_ERR,0.6)
            self.pop.go(r,c,ok=False)
            self.shake.go()
            self.snd.play("wrong")
            self.ft.add("-50",cx,cy,TXT_ERR)
            self.ptcl.burst(cx,cy,[CELL_ERR,(255,110,110)],12)
            if self.lives<=0:
                pygame.time.delay(250)
                self.state="over"; self.snd.play("lose")
        else:
            self.combo+=1; self.maxc=max(self.maxc,self.combo)
            bonus=10+(self.combo-1)*5
            tbonus=max(0,30-int(self.elapsed//60)*5)
            pts=bonus+tbonus; self.score+=pts
            self.flash.add(r,c,CELL_OK,0.35)
            self.pop.go(r,c,ok=True)
            self.snd.play("ok")
            lbl=f"+{pts}"+(f" x{self.combo}" if self.combo>1 else "")
            self.ft.add(lbl,cx,cy,TXT_OK)
            self.ptcl.burst(cx,cy,[CELL_OK,ACCENT2,(200,255,200)],8)
            self._peer_notes(r,c,digit)
            if self._won():
                pygame.time.delay(150); self.state="win"
                self.snd.play("win"); self._win_ptcl()

    def _peer_notes(self,r,c,digit):
        for cc in range(9): self.notes[r][cc].discard(digit)
        for rr in range(9): self.notes[rr][c].discard(digit)
        br,bc=(r//3)*3,(c//3)*3
        for dr in range(3):
            for dc in range(3): self.notes[br+dr][bc+dc].discard(digit)

    def _erase(self):
        if not self.sel: return
        r,c=self.sel
        if self.orig[r][c]!=0: return
        self.grid[r][c]=0; self.notes[r][c].clear()

    def _toggle_notes(self):
        self.nmode=not self.nmode
        self.bNote.text=f"Notes: {'ON' if self.nmode else 'OFF'}"
        self.bNote.col=ACCENT2 if self.nmode else (55,55,100)

    def _hint(self):
        if self.hints<=0 or self.state!="playing" or not self.sol: return
        for r in range(9):
            for c in range(9):
                if self.orig[r][c]==0 and self.grid[r][c]==0:
                    v=self.sol[r][c]
                    self.grid[r][c]=v; self.notes[r][c].clear()
                    self.hcells.add((r,c)); self.hints-=1
                    self.score=max(0,self.score-100)
                    self.flash.add(r,c,CELL_HINT,0.5)
                    self.pop.go(r,c,ok=True)
                    self.snd.play("hint")
                    cx,cy=self._cc(r,c)
                    self.ft.add("Hint -100",cx,cy,TXT_HINT)
                    self._peer_notes(r,c,v)
                    if self._won():
                        self.state="win"; self.snd.play("win"); self._win_ptcl()
                    return

    def _autosolve(self):
        if not self.sol: return
        for r in range(9):
            for c in range(9): self.grid[r][c]=self.sol[r][c]
        self.score=max(0,self.score-500)
        self.state="win"; self.snd.play("win"); self._win_ptcl()

    def _start_anim(self):
        if not self.sol: return
        self.anim=True
        self.asteps=[(r,c,self.sol[r][c])
                     for r in range(9) for c in range(9)
                     if self.orig[r][c]==0 and self.grid[r][c]==0]
        self.asteps.sort(key=lambda x:(x[0]//3*3+x[1]//3))
        self.aidx=0; self.atimer=0

    def _won(self):
        if not self.sol: return False
        return all(self.grid[r][c]==self.sol[r][c] for r in range(9) for c in range(9))

    def _win_ptcl(self):
        cols=[ACCENT,ACCENT2,GOLD,(255,100,150),TXT_OK]
        for _ in range(45):
            self.ptcl.burst(random.randint(self.OX,self.OX+self.BS),
                            random.randint(self.OY,self.OY+self.BS),cols,3)

    # ── Update ────────────────────────────────────────────────────────────────
    def _update(self, dt):
        if self.state=="playing":
            self.elapsed=time.time()-self.t0
            self.flash.clean()
            if self.anim:
                self.atimer+=dt
                while self.atimer>=0.055 and self.aidx<len(self.asteps):
                    r,c,v=self.asteps[self.aidx]
                    self.grid[r][c]=v
                    self.flash.add(r,c,CELL_HINT,0.28)
                    self.pop.go(r,c,ok=True)
                    self.aidx+=1; self.atimer-=0.055
                if self.aidx>=len(self.asteps):
                    self.anim=False; self.state="win"
                    self.snd.play("win"); self._win_ptcl()
        elif self.state=="win":
            if random.random()<0.18:
                self.ptcl.confetti(pygame.Rect(self.OX,self.OY,self.BS,self.BS))

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        ox,oy=self.shake.off()
        self._bg()

        if self.state=="menu":
            self._d_menu()
        else:
            sx = ox if self.state=="playing" else 0
            sy = oy if self.state=="playing" else 0
            self._d_header(sx,sy)
            self._d_board(sx,sy)
            self._d_panel()
            self.ft.draw(self.screen,self.fScore)
            if self.state=="over": self._d_over()
            if self.state=="win":  self._d_win()

        self.ptcl.update_draw(self.screen)
        pygame.display.flip()

    def _bg(self):
        if self._bgsurf is None:
            self._bgsurf=pygame.Surface((W,H)); self._bgsurf.fill(BG)
            for i in range(0,W,60): pygame.draw.line(self._bgsurf,(18,21,38),(i,0),(i,H),1)
            for i in range(0,H,60): pygame.draw.line(self._bgsurf,(18,21,38),(0,i),(W,i),1)
        self.screen.blit(self._bgsurf,(0,0))

    # ── Menu ──────────────────────────────────────────────────────────────────
    def _d_menu(self):
        t=self.fTitle.render("SUDOKU PREMIUM",True,ACCENT)
        self.screen.blit(t,t.get_rect(centerx=W//2,top=115))
        s=self.fSM.render("AI-Powered  |  CSP Solver  |  Backtracking + AC-3 + MRV + LCV",True,TXT_DIM)
        self.screen.blit(s,s.get_rect(centerx=W//2,top=178))
        pygame.draw.line(self.screen,ACCENT,(W//2-210,205),(W//2+210,205),1)

        dl=self.fSM.render("SELECT DIFFICULTY",True,TXT_DIM)
        self.screen.blit(dl,dl.get_rect(centerx=W//2,top=260))

        diffs=list(PUZZLES); bw=(W-200)//4
        for i,d in enumerate(diffs):
            bx=100+i*(bw+10); r=pygame.Rect(bx,300,bw,90)
            col=self.DCOLS[d]; sel=self.diff==d
            rrect(self.screen,col if sel else (28,32,52),r,12)
            pygame.draw.rect(self.screen,col,r,2,border_radius=12)
            lb=self.fUI.render(d,True,TXT_WHITE if sel else col)
            self.screen.blit(lb,lb.get_rect(centerx=r.centerx,centery=r.centery))

        play=pygame.Rect(W//2-130,430,260,60)
        rrect(self.screen,ACCENT,play,14)
        pt=self.fBig.render("PLAY",True,TXT_WHITE)
        self.screen.blit(pt,pt.get_rect(center=play.center))

        for i,h in enumerate([
            "Click a cell, then press 1-9 to enter a number",
            "H = Hint    N = Toggle Notes    Backspace = Erase    Arrows = Navigate"
        ]):
            ht=self.fSM.render(h,True,TXT_DIM)
            self.screen.blit(ht,ht.get_rect(centerx=W//2,top=520+i*22))

    # ── Header — FIXED: no overlap ────────────────────────────────────────────
    def _d_header(self, ox=0, oy=0):
        # Row 1: title | diff | hearts | timer
        # Row 2: score | moves/mistakes
        bx=self.OX+ox

        # Title (left)
        t=self.fScore.render("SUDOKU PREMIUM",True,TXT_DIM)
        self.screen.blit(t,(bx, 18+oy))

        # Difficulty label (after title, with pipe)
        pipe=self.fScore.render("|",True,(60,60,90))
        self.screen.blit(pipe,(bx+t.get_width()+10, 18+oy))
        dl=self.fScore.render(self.diff,True,self.DCOLS[self.diff])
        self.screen.blit(dl,(bx+t.get_width()+26, 18+oy))

        # Hearts — fixed position, no overlap with diff text
        hx = bx + t.get_width() + 26 + dl.get_width() + 18
        for i in range(self.MAX_LIVES):
            col = HEART_ON if i < self.lives else HEART_OFF
            ht  = self.fHeart.render(chr(9829), True, col)  # ♥
            self.screen.blit(ht, (hx + i*28, 17+oy))

        # Timer (right-aligned to board edge)
        e=int(self.elapsed); m,s=e//60,e%60
        tc=GOLD if e<120 else TXT_WHITE
        tt=self.fScore.render(f"{m:02d}:{s:02d}",True,tc)
        self.screen.blit(tt,(self.OX+self.BS-tt.get_width(), 18+oy))

        # Row 2: score (left) | moves+mistakes (right)
        sc=self.fBig.render(f"Score: {self.score}",True,ACCENT)
        self.screen.blit(sc,(bx, 44+oy))

        mv=self.fSM.render(f"Moves: {self.moves}    Mistakes: {self.err}",True,TXT_DIM)
        self.screen.blit(mv,(self.OX+self.BS-mv.get_width(), 50+oy))

        # Combo (only if active, centered)
        if self.combo>1:
            pulse=abs(math.sin(time.time()*5))*0.25+0.75
            cc=tuple(int(c*pulse) for c in GOLD)
            ct=self.fCombo.render(f"x{self.combo} COMBO",True,cc)
            self.screen.blit(ct,(bx+self.BS//2-ct.get_width()//2, 46+oy))

    # ── Board ─────────────────────────────────────────────────────────────────
    def _d_board(self, ox=0, oy=0):
        bx=self.OX+ox; by=self.OY+oy; cs=self.CS
        sel=self.sel
        sv=self.grid[sel[0]][sel[1]] if sel else 0

        for r in range(9):
            for c in range(9):
                rx=bx+c*cs; ry=by+r*cs
                rect=pygame.Rect(rx+1,ry+1,cs-2,cs-2)
                val=self.grid[r][c]
                fixed=self.orig[r][c]!=0
                hint=(r,c) in self.hcells
                fc,fa=self.flash.get(r,c)

                if sel and (r,c)==sel:          base=CELL_SEL
                elif sel and (r==sel[0] or c==sel[1] or
                              (r//3==sel[0]//3 and c//3==sel[1]//3)): base=CELL_REL
                elif sv and val==sv and val!=0:  base=CELL_SAME
                elif fixed:                      base=CELL_FIXED
                else:                            base=CELL_EMPTY

                if fc and fa>0: base=lc(base,fc,fa/200)
                pygame.draw.rect(self.screen,base,rect,border_radius=5)

                if val!=0:
                    sc=self.pop.scale(r,c)
                    if hint:       nc=TXT_HINT
                    elif fixed:    nc=TXT_FIXED
                    elif self.sol and val!=self.sol[r][c]: nc=TXT_ERR
                    else:          nc=TXT_USER
                    f=self._sf_get(36*sc) if sc!=1.0 else self.fCell
                    nt=f.render(str(val),True,nc)
                    self.screen.blit(nt,(rx+cs//2-nt.get_width()//2,
                                        ry+cs//2-nt.get_height()//2))
                elif self.notes[r][c] and not fixed:
                    nw=cs//3
                    for n in range(1,10):
                        if n in self.notes[r][c]:
                            nr_=(n-1)//3; nc_=(n-1)%3
                            nt=self.fNote.render(str(n),True,TXT_NOTE)
                            self.screen.blit(nt,(rx+nc_*nw+nw//2-nt.get_width()//2,
                                                 ry+nr_*nw+nw//2-nt.get_height()//2))

        for i in range(10):
            t=3 if i%3==0 else 1; c=LINE_THICK if i%3==0 else LINE_THIN
            pygame.draw.line(self.screen,c,(bx+i*cs,by),(bx+i*cs,by+9*cs),t)
            pygame.draw.line(self.screen,c,(bx,by+i*cs),(bx+9*cs,by+i*cs),t)
        pygame.draw.rect(self.screen,ACCENT,(bx-1,by-1,9*cs+2,9*cs+2),2,border_radius=4)

        if self.anim:
            ov=pygame.Surface((9*cs,9*cs),pygame.SRCALPHA); ov.fill((0,0,0,32))
            self.screen.blit(ov,(bx,by))
            t=self.fSM.render("Solving...  ESC to stop",True,ACCENT2)
            self.screen.blit(t,t.get_rect(centerx=bx+9*cs//2,centery=by-20))

    # ── Panel — FIXED: no label overlaps ─────────────────────────────────────
    def _d_panel(self):
        px=self.PX; pw=self.PW
        rrect(self.screen,PANEL_BG,pygame.Rect(px-8,108,pw+16,H-115),12)

        def sec(text,y):
            lb=self.fSM.render(text,True,TXT_DIM)
            self.screen.blit(lb,(px,y))
            pygame.draw.line(self.screen,(48,52,85),(px,y+17),(px+pw,y+17),1)

        # ── Section: Difficulty ──────────────────────────────────────────────
        sec("DIFFICULTY",118)
        col=self.DCOLS[self.diff]
        dt=self.fUI.render(self.diff,True,col)
        self.screen.blit(dt,(px+10,140))

        # ── Section: Stats ───────────────────────────────────────────────────
        sec("STATS",172)
        rows=[("Score",        f"{self.score}",     ACCENT),
              ("Hints left",   f"{self.hints}/{self.MAX_HINTS}", ACCENT2),
              ("Combo",        f"x{self.combo}" if self.combo>1 else "-", GOLD),
              ("Best combo",   f"x{self.maxc}",    TXT_DIM)]
        for i,(k,v,c) in enumerate(rows):
            ky=self.fSM.render(k,True,TXT_DIM)
            vy=self.fUI.render(v,True,c)
            self.screen.blit(ky,(px,194+i*20))
            self.screen.blit(vy,(px+pw-vy.get_width(),194+i*20))

        # ── Section: Difficulty selector ─────────────────────────────────────
        sec("CHANGE DIFF",280)
        for b in self.dBtns: b.draw(self.screen)

        # ── Section: Actions ─────────────────────────────────────────────────
        sec("ACTIONS",374)
        for b in [self.bHint,self.bNote,self.bSolve,self.bAnim,self.bNew,self.bMenu]:
            b.draw(self.screen)

        # ── Hint count indicator on hint button ──────────────────────────────
        hc=self.fSM.render(f"{self.hints} left",True,TXT_DIM)
        self.screen.blit(hc,(self.bHint.rect.right-hc.get_width()-8,
                             self.bHint.rect.top-hc.get_height()))

    # ── End screens ───────────────────────────────────────────────────────────
    def _d_over(self):
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((8,5,15,195))
        self.screen.blit(ov,(0,0))
        t=self.fHuge.render("GAME  OVER",True,(215,50,80))
        self.screen.blit(t,t.get_rect(centerx=W//2,centery=H//2-75))
        s=self.fSub.render(f"Out of lives  |  Final score: {self.score}",True,TXT_DIM)
        self.screen.blit(s,s.get_rect(centerx=W//2,centery=H//2-18))
        for y,text,col,tc in [(H//2+38,"Try Again  (R)",(70,28,28),TXT_WHITE),
                               (H//2+100,"Main Menu",(40,28,58),TXT_DIM)]:
            rrect(self.screen,col,pygame.Rect(W//2-120,y,240,50),12)
            lb=self.fUI.render(text,True,tc)
            self.screen.blit(lb,lb.get_rect(centerx=W//2,centery=y+25))

    def _d_win(self):
        ov=pygame.Surface((W,H),pygame.SRCALPHA); ov.fill((5,14,8,175))
        self.screen.blit(ov,(0,0))
        pulse=abs(math.sin(time.time()*2))*0.2+0.8
        col=tuple(int(c*pulse) for c in GOLD)
        t=self.fHuge.render("SOLVED!",True,col)
        self.screen.blit(t,t.get_rect(centerx=W//2,centery=H//2-95))
        e=int(self.elapsed); m,s=e//60,e%60
        for i,(line,c) in enumerate([
            (f"Score: {self.score}",ACCENT),
            (f"Time: {m:02d}:{s:02d}",TXT_WHITE),
            (f"Mistakes: {self.err}    Best Combo: x{self.maxc}",TXT_DIM)
        ]):
            lt=self.fSub.render(line,True,c)
            self.screen.blit(lt,lt.get_rect(centerx=W//2,centery=H//2-28+i*30))
        for y,text,col,tc in [(H//2+90,"Play Again  (R)",TXT_OK,BG),
                               (H//2+152,"Main Menu",(40,28,58),TXT_DIM)]:
            rrect(self.screen,col,pygame.Rect(W//2-120,y,240,50),12)
            lb=self.fUI.render(text,True,tc)
            self.screen.blit(lb,lb.get_rect(centerx=W//2,centery=y+25))

    def _cc(self,r,c):
        return(self.OX+c*self.CS+self.CS//2, self.OY+r*self.CS+self.CS//2)


def main():
    Game().run()

if __name__=="__main__":
    main()

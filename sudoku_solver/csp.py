"""
csp.py — Core Constraint Satisfaction Problem (CSP) engine
Provides domain management, arc consistency (AC-3), and constraint propagation
for the Sudoku solver.
"""

from copy import deepcopy
from collections import deque


class SudokuCSP:
    """
    Encapsulates the Sudoku puzzle as a CSP:
      - Variables : 81 cells (row, col) ∈ [0..8]²
      - Domains   : set of {1..9} for empty cells, {given} for filled cells
      - Constraints: all-different for each row, column, and 3×3 box
    """

    # Pre-compute peers for every cell (row-mates + col-mates + box-mates)
    _PEERS: dict = {}

    @classmethod
    def _build_peers(cls) -> None:
        if cls._PEERS:
            return
        for r in range(9):
            for c in range(9):
                peers = set()
                # Same row
                for cc in range(9):
                    if cc != c:
                        peers.add((r, cc))
                # Same column
                for rr in range(9):
                    if rr != r:
                        peers.add((rr, c))
                # Same 3×3 box
                br, bc = (r // 3) * 3, (c // 3) * 3
                for dr in range(3):
                    for dc in range(3):
                        peer = (br + dr, bc + dc)
                        if peer != (r, c):
                            peers.add(peer)
                cls._PEERS[(r, c)] = frozenset(peers)

    def __init__(self, grid: list[list[int]]):
        """
        grid: 9×9 list of ints; 0 means empty cell.
        """
        SudokuCSP._build_peers()
        self.domains: dict[tuple, set] = {}
        for r in range(9):
            for c in range(9):
                val = grid[r][c]
                self.domains[(r, c)] = {val} if val != 0 else set(range(1, 10))

    # ------------------------------------------------------------------
    # Arc helpers
    # ------------------------------------------------------------------

    def get_peers(self, var: tuple) -> frozenset:
        return self._PEERS[var]

    def get_arcs(self) -> list[tuple]:
        """Return all constraint arcs (Xi, Xj) where Xi and Xj are peers."""
        arcs = []
        for var, peers in self._PEERS.items():
            for peer in peers:
                arcs.append((var, peer))
        return arcs

    # ------------------------------------------------------------------
    # Constraint check
    # ------------------------------------------------------------------

    def is_consistent(self, var: tuple, value: int, assignment: dict) -> bool:
        """Return True if assigning *value* to *var* violates no constraint."""
        for peer in self._PEERS[var]:
            if assignment.get(peer) == value:
                return False
        return True

    # ------------------------------------------------------------------
    # AC-3 Arc Consistency
    # ------------------------------------------------------------------

    def ac3(self, domains: dict) -> bool:
        """
        Enforce arc consistency using AC-3.
        Mutates *domains* in place.
        Returns False if a domain becomes empty (contradiction detected).
        """
        queue = deque(self.get_arcs())

        while queue:
            xi, xj = queue.popleft()
            if self._revise(domains, xi, xj):
                if not domains[xi]:          # empty domain → failure
                    return False
                # Re-examine all arcs pointing into xi
                for peer in self._PEERS[xi]:
                    if peer != xj:
                        queue.append((peer, xi))
        return True

    @staticmethod
    def _revise(domains: dict, xi: tuple, xj: tuple) -> bool:
        """
        Remove values from domains[xi] that have no support in domains[xj].
        Returns True if the domain of xi was reduced.
        """
        revised = False
        for val in list(domains[xi]):
            # val is inconsistent if xj has only that value (or no other option)
            if domains[xj] == {val}:
                domains[xi].discard(val)
                revised = True
        return revised

    # ------------------------------------------------------------------
    # Forward Checking
    # ------------------------------------------------------------------

    def forward_check(self, var: tuple, value: int, domains: dict) -> bool:
        """
        After assigning *value* to *var*, remove *value* from all peers' domains.
        Returns False if any peer domain becomes empty.
        """
        for peer in self._PEERS[var]:
            if value in domains[peer]:
                domains[peer].discard(value)
                if not domains[peer]:
                    return False
        return True

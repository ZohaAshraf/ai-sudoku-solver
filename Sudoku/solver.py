"""
solver.py — Backtracking solver with advanced heuristics
Implements:
  • Backtracking Search
  • Forward Checking
  • AC-3 pre-processing
  • MRV  (Minimum Remaining Values) variable ordering
  • Degree Heuristic (tie-breaking for MRV)
  • LCV  (Least Constraining Value) value ordering
"""

from copy import deepcopy
from csp import SudokuCSP


class SudokuSolver:
    """
    Solves a Sudoku puzzle via backtracking with constraint propagation.

    Usage
    -----
    solver = SudokuSolver(grid)
    result = solver.solve()
    # result.solution  → 9×9 list or None
    # result.stats     → dict with backtrack_calls, failures, etc.
    """

    def __init__(self, grid: list[list[int]]):
        self.original_grid = [row[:] for row in grid]

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def solve(self) -> "SolveResult":
        csp = SudokuCSP(self.original_grid)
        domains = deepcopy(csp.domains)

        stats = {"backtrack_calls": 0, "failures": 0}

        # --- Pre-processing: run AC-3 on the initial domains ---------------
        if not csp.ac3(domains):
            stats["failures"] += 1
            return SolveResult(None, stats)

        assignment = {}
        # Seed assignment from any singleton domains
        for var, dom in domains.items():
            if len(dom) == 1:
                assignment[var] = next(iter(dom))

        solution_assignment = self._backtrack(assignment, domains, csp, stats)

        if solution_assignment is None:
            return SolveResult(None, stats)

        grid = [[0] * 9 for _ in range(9)]
        for (r, c), val in solution_assignment.items():
            grid[r][c] = val
        return SolveResult(grid, stats)

    # ------------------------------------------------------------------ #
    #  Core backtracking                                                   #
    # ------------------------------------------------------------------ #

    def _backtrack(
        self,
        assignment: dict,
        domains: dict,
        csp: SudokuCSP,
        stats: dict,
    ) -> dict | None:

        stats["backtrack_calls"] += 1

        # Goal check — all 81 cells assigned
        if len(assignment) == 81:
            return assignment

        # 1. Variable selection: MRV + Degree heuristic
        var = self._select_unassigned_variable(assignment, domains, csp)

        # 2. Value ordering: LCV
        for value in self._order_domain_values(var, assignment, domains, csp):

            if csp.is_consistent(var, value, assignment):
                # Make a local copy of domains for this branch
                local_domains = deepcopy(domains)
                local_domains[var] = {value}

                # 3. Forward Checking
                fc_ok = csp.forward_check(var, value, local_domains)

                if fc_ok:
                    # 4. Incremental AC-3 (maintain arc consistency)
                    arc_ok = csp.ac3(local_domains)

                    if arc_ok:
                        assignment[var] = value

                        result = self._backtrack(
                            assignment, local_domains, csp, stats
                        )
                        if result is not None:
                            return result

                        del assignment[var]

                stats["failures"] += 1

        return None  # Trigger backtrack

    # ------------------------------------------------------------------ #
    #  MRV heuristic (+ Degree tie-breaking)                               #
    # ------------------------------------------------------------------ #

    def _select_unassigned_variable(
        self,
        assignment: dict,
        domains: dict,
        csp: SudokuCSP,
    ) -> tuple:
        """
        MRV: choose the unassigned variable with the fewest legal values.
        Tie-break with the Degree heuristic (most constraints on unassigned peers).
        """
        unassigned = [v for v in domains if v not in assignment]

        # MRV score: domain size
        min_remaining = min(len(domains[v]) for v in unassigned)
        mrv_candidates = [v for v in unassigned if len(domains[v]) == min_remaining]

        if len(mrv_candidates) == 1:
            return mrv_candidates[0]

        # Degree heuristic: count unassigned peers
        def degree(var):
            return sum(1 for p in csp.get_peers(var) if p not in assignment)

        return max(mrv_candidates, key=degree)

    # ------------------------------------------------------------------ #
    #  LCV value ordering                                                  #
    # ------------------------------------------------------------------ #

    def _order_domain_values(
        self,
        var: tuple,
        assignment: dict,
        domains: dict,
        csp: SudokuCSP,
    ) -> list:
        """
        LCV: order values by ascending number of constraints imposed on peers.
        The value that rules out the fewest choices for neighbours comes first.
        """
        def count_constraints(value):
            count = 0
            for peer in csp.get_peers(var):
                if peer not in assignment and value in domains[peer]:
                    count += 1
            return count

        return sorted(domains[var], key=count_constraints)


# ------------------------------------------------------------------ #
#  Result container                                                    #
# ------------------------------------------------------------------ #

class SolveResult:
    """Lightweight data-class for solver output."""

    def __init__(self, solution: list[list[int]] | None, stats: dict):
        self.solution = solution
        self.stats = stats
        self.success = solution is not None

    def __repr__(self):
        return (
            f"SolveResult(success={self.success}, "
            f"backtracks={self.stats['backtrack_calls']}, "
            f"failures={self.stats['failures']})"
        )

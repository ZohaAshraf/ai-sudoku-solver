"""
solver.py — Backtracking solver with advanced heuristics
"""

from copy import deepcopy
from csp import SudokuCSP


class SudokuSolver:
    def __init__(self, grid: list[list[int]]):
        self.original_grid = [row[:] for row in grid]

    def solve(self) -> "SolveResult":
        csp = SudokuCSP(self.original_grid)
        domains = deepcopy(csp.domains)
        stats = {"backtrack_calls": 0, "failures": 0}

        if not csp.ac3(domains):
            stats["failures"] += 1
            return SolveResult(None, stats)

        assignment = {}
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

    def solve_steps(self) -> list:
        """Solve and return list of (row, col, value) steps."""
        result = self.solve()
        if not result.success:
            return []
        steps = []
        for r in range(9):
            for c in range(9):
                if self.original_grid[r][c] == 0:
                    steps.append((r, c, result.solution[r][c]))
        return steps

    def get_hint(self, current_grid: list[list[int]]) -> tuple | None:
        """Return (row, col, value) for one hint cell."""
        result = SudokuSolver(current_grid).solve()
        if not result.success:
            return None
        for r in range(9):
            for c in range(9):
                if current_grid[r][c] == 0:
                    return (r, c, result.solution[r][c])
        return None

    def _backtrack(self, assignment, domains, csp, stats):
        stats["backtrack_calls"] += 1
        if len(assignment) == 81:
            return assignment

        var = self._select_unassigned_variable(assignment, domains, csp)
        for value in self._order_domain_values(var, assignment, domains, csp):
            if csp.is_consistent(var, value, assignment):
                local_domains = deepcopy(domains)
                local_domains[var] = {value}
                if csp.forward_check(var, value, local_domains):
                    if csp.ac3(local_domains):
                        assignment[var] = value
                        result = self._backtrack(assignment, local_domains, csp, stats)
                        if result is not None:
                            return result
                        del assignment[var]
                stats["failures"] += 1
        return None

    def _select_unassigned_variable(self, assignment, domains, csp):
        unassigned = [v for v in domains if v not in assignment]
        min_remaining = min(len(domains[v]) for v in unassigned)
        mrv_candidates = [v for v in unassigned if len(domains[v]) == min_remaining]
        if len(mrv_candidates) == 1:
            return mrv_candidates[0]
        def degree(var):
            return sum(1 for p in csp.get_peers(var) if p not in assignment)
        return max(mrv_candidates, key=degree)

    def _order_domain_values(self, var, assignment, domains, csp):
        def count_constraints(value):
            return sum(1 for peer in csp.get_peers(var)
                       if peer not in assignment and value in domains[peer])
        return sorted(domains[var], key=count_constraints)


class SolveResult:
    def __init__(self, solution, stats):
        self.solution = solution
        self.stats = stats
        self.success = solution is not None

    def __repr__(self):
        return (f"SolveResult(success={self.success}, "
                f"backtracks={self.stats['backtrack_calls']})")

"""Exact support selection via guarded equalities and implicit hitting sets."""

from contextlib import ExitStack
from dataclasses import dataclass
from typing import Iterable, Mapping

from pysat.examples.rc2 import RC2
from pysat.formula import WCNF
from pysat.solvers import Solver

from .dimacs import CNF, InputError

BACKENDS = ("cadical195", "glucose3", "minisat22")


class InfeasibleError(ValueError):
    """A pair is satisfiable even with all shared variables identified."""

    def __init__(self, pair_index: int):
        self.pair_index = pair_index
        super().__init__(f"pair {pair_index + 1}: A AND B is satisfiable; no interpolation support exists")


@dataclass(frozen=True)
class SelectionResult:
    selected_variables: tuple[int, ...]
    min_cost: int
    candidates: tuple[int, ...]
    pair_count: int
    iterations: int
    correction_sets: int
    sat_calls: int


class _PairOracle:
    def __init__(self, a: CNF, b: CNF, backend: str, stack: ExitStack):
        avars, bvars = a.variables, b.variables
        self.shared = tuple(sorted(avars & bvars))
        # Dense private namespaces avoid allocating up to a sparse DIMACS bound.
        amap = {v: i + 1 for i, v in enumerate(sorted(avars))}
        bmap = {v: len(amap) + i + 1 for i, v in enumerate(sorted(bvars))}
        self.selectors = {v: len(amap) + len(bmap) + i + 1
                          for i, v in enumerate(self.shared)}
        self.solver = stack.enter_context(Solver(name=backend))
        self.calls = 0
        for formula, mapping in ((a, amap), (b, bmap)):
            for clause in formula.clauses:
                self.solver.add_clause([mapping[abs(l)] if l > 0 else -mapping[abs(l)]
                                        for l in clause])
        for var, selector in self.selectors.items():
            self.solver.add_clause([-selector, -amap[var], bmap[var]])
            self.solver.add_clause([-selector, amap[var], -bmap[var]])

    def sat(self, selected: Iterable[int]) -> bool:
        self.calls += 1
        # Omitted selectors can be false; no disabled equality is required.
        answer = self.solver.solve(assumptions=[self.selectors[v] for v in selected
                                              if v in self.selectors])
        if answer is None:
            raise RuntimeError("SAT backend returned unknown; no optimum certified")
        return answer

    def correction(self, selected: set[int]) -> set[int]:
        """Grow a known SAT set to an MSS; its complement must be hit."""
        enabled = set(self.shared) & selected
        for var in self.shared:
            if var not in enabled and self.sat(enabled | {var}):
                enabled.add(var)
        return set(self.shared) - enabled


def select_variables(
    pairs: Iterable[tuple[CNF, CNF]],
    costs: Mapping[int, int] | None = None,
    *,
    solver: str = "cadical195",
) -> SelectionResult:
    """Return one globally minimum-cost support sufficient for every pair.

    Costs override unit weights and must be positive integers. IDs are shared
    across pairs and charged once. Raises InfeasibleError for a satisfiable
    pair and InputError for invalid arguments. Native solvers are always freed.
    """
    pairs = tuple(pairs)
    if not pairs:
        raise InputError("at least one CNF pair is required")
    if solver not in BACKENDS:
        raise InputError(f"unsupported solver {solver!r}; choose from {', '.join(BACKENDS)}")
    for pair in pairs:
        if len(pair) != 2 or not all(isinstance(c, CNF) for c in pair):
            raise InputError("each pair must contain two CNF objects")
    candidates = tuple(sorted(set().union(*(a.variables & b.variables for a, b in pairs))))
    weights = dict.fromkeys(candidates, 1)
    for var, cost in (costs if costs is not None else {}).items():
        if type(var) is not int or var not in weights:
            raise InputError(f"cost variable {var!r} is not shared in any input pair")
        if type(cost) is not int or cost <= 0:
            raise InputError(f"cost for variable {var} must be a positive integer")
        weights[var] = cost

    with ExitStack() as stack:
        oracles = [_PairOracle(a, b, solver, stack) for a, b in pairs]
        for index, oracle in enumerate(oracles):
            if oracle.sat(oracle.shared):
                raise InfeasibleError(index)
        variable_map = {v: i + 1 for i, v in enumerate(candidates)}
        objective = WCNF()
        for var in candidates:
            objective.append([-variable_map[var]], weight=weights[var])
        optimizer = stack.enter_context(RC2(objective, solver=solver))
        iterations = corrections = 0
        while True:
            iterations += 1
            model = optimizer.compute()
            if model is None:
                raise RuntimeError("hitting-set optimization failed; no optimum certified")
            positive = {lit for lit in model if lit > 0}
            selected = {v for v in candidates if variable_map[v] in positive}
            failed = False
            for oracle in oracles:
                if oracle.sat(selected):
                    correction = oracle.correction(selected)
                    if not correction:
                        raise RuntimeError("empty correction set after feasibility validation")
                    optimizer.add_clause([variable_map[v] for v in sorted(correction)])
                    corrections += 1
                    failed = True
            if not failed:
                return SelectionResult(
                    tuple(sorted(selected)), sum(weights[v] for v in selected),
                    candidates, len(pairs), iterations, corrections,
                    sum(o.calls for o in oracles),
                )

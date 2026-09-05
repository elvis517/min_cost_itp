"""Check this fixture's partition structure and SAT/UNSAT contract."""

from pathlib import Path
import hashlib
import json

from min_cost_itp import read_costs, read_dimacs
from pysat.solvers import Solver


def main():
    here = Path(__file__).resolve().parent
    provenance = json.loads((here / "provenance.json").read_text())
    formulas = {side: read_dimacs(here / f"{side}.cnf") for side in "AB"}
    for side, formula in formulas.items():
        expected = provenance["cnf"][side]
        assert hashlib.sha256((here / f"{side}.cnf").read_bytes()).hexdigest() == expected["sha256"]
        assert formula.nvars == expected["declared_variable_bound"]
        assert len(formula.clauses) == expected["clauses"]
        assert len(formula.variables) == expected["used_variables"]
    shared = formulas["A"].variables & formulas["B"].variables
    names = {}
    for line in (here / "shared_variables.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            var, name = line.split()
            assert int(var) not in names
            names[int(var)] = name
    assert shared == set(names) == set(range(271, 532))
    assert all(name.startswith("s1_") for name in names.values())
    assert set(read_costs(here / "costs.txt")) == shared
    print(f"Shared boundary: {len(shared)} variables, IDs 271..531", flush=True)
    for side, formula in formulas.items():
        with Solver(name="cadical195", bootstrap_with=formula.clauses) as solver:
            assert solver.solve() is True, f"{side} should be SAT"
        print(f"{side}: SAT", flush=True)
    with Solver(name="cadical195") as solver:
        for formula in formulas.values():
            solver.append_formula(formula.clauses)
        assert solver.solve() is False, "A AND B should be UNSAT"
    print("A AND B: UNSAT", flush=True)
    print("Fixture verified; minimum support search was not run.", flush=True)


if __name__ == "__main__":
    main()

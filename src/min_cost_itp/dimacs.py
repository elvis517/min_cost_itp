"""Strict DIMACS and variable-cost input, without invoking a solver."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class InputError(ValueError):
    """Malformed formula, costs, or unsupported input."""


@dataclass(frozen=True)
class CNF:
    """Immutable CNF. Variables are positive DIMACS IDs; clauses omit zero."""

    clauses: tuple[tuple[int, ...], ...]
    nvars: int

    def __post_init__(self):
        if type(self.nvars) is not int or self.nvars < 0:
            raise InputError("nvars must be a nonnegative integer")
        clauses = tuple(tuple(c) for c in self.clauses)
        for clause in clauses:
            for lit in clause:
                if type(lit) is not int or lit == 0 or abs(lit) > self.nvars:
                    raise InputError(f"literal {lit!r} is outside 1..{self.nvars}")
        object.__setattr__(self, "clauses", clauses)

    @property
    def variables(self) -> frozenset[int]:
        return frozenset(abs(lit) for c in self.clauses for lit in c)


def parse_dimacs(lines: Iterable[str], source: str = "<input>") -> CNF:
    header = None
    clauses = []
    pending = []
    for number, line in enumerate(lines, 1):
        fields = line.split()
        if not fields or fields[0] == "c":
            continue
        location = f"{source}:{number}"
        if fields[0] == "p":
            if header is not None or len(fields) != 4 or fields[1] != "cnf":
                raise InputError(f"{location}: expected a single 'p cnf N M' header")
            try:
                header = (int(fields[2]), int(fields[3]))
            except ValueError as exc:
                raise InputError(f"{location}: noninteger header count") from exc
            if min(header) < 0:
                raise InputError(f"{location}: negative header count")
            continue
        if header is None:
            raise InputError(f"{location}: clause before DIMACS header")
        for field in fields:
            try:
                lit = int(field)
            except ValueError as exc:
                raise InputError(f"{location}: invalid literal {field!r}") from exc
            if abs(lit) > header[0]:
                raise InputError(f"{location}: literal {lit} exceeds declared variable bound")
            if lit == 0:
                clauses.append(tuple(pending))
                pending.clear()
                if len(clauses) > header[1]:
                    raise InputError(f"{location}: too many clauses")
            else:
                pending.append(lit)
    if header is None:
        raise InputError(f"{source}: missing DIMACS header")
    if pending:
        raise InputError(f"{source}: last clause is missing its terminating zero")
    if len(clauses) != header[1]:
        raise InputError(f"{source}: declared {header[1]} clauses, read {len(clauses)}")
    return CNF(tuple(clauses), header[0])


def read_dimacs(path: str | Path) -> CNF:
    with open(path, encoding="utf-8") as stream:
        return parse_dimacs(stream, str(path))


def read_costs(path: str | Path) -> dict[int, int]:
    """Read optional overrides, one 'variable positive_integer_cost' per line."""
    costs = {}
    with open(path, encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            fields = line.split()
            if not fields or fields[0] in ("c", "#") or line.lstrip().startswith("#"):
                continue
            location = f"{path}:{number}"
            if len(fields) != 2:
                raise InputError(f"{location}: expected 'variable cost'")
            try:
                var, cost = map(int, fields)
            except ValueError as exc:
                raise InputError(f"{location}: variable and cost must be integers") from exc
            if var <= 0 or cost <= 0:
                raise InputError(f"{location}: variable and cost must be positive")
            if var in costs:
                raise InputError(f"{location}: duplicate cost for variable {var}")
            costs[var] = cost
    return costs

"""Command-line entry point. Stdout is reserved for results."""

import argparse
from dataclasses import asdict
import json
import sys

from . import (BACKENDS, InfeasibleError, InputError, __version__, read_costs,
               read_dimacs, select_variables)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Select exact minimum-cost interpolation variables for CNF pairs.",
        epilog="Example: min-cost-itp A.cnf B.cnf --costs costs.txt --json",
    )
    parser.add_argument("files", nargs="*", metavar="CNF", help="A B [A2 B2 ...]")
    parser.add_argument("--pair", nargs=2, action="append", default=[], metavar=("A", "B"),
                        help="input pair; repeat for a common support across pairs")
    parser.add_argument("--costs", metavar="FILE", action="append",
                        help="optional 'variable positive_cost' overrides (one file)")
    parser.add_argument("--solver", choices=BACKENDS, default="cadical195")
    parser.add_argument("--json", action="store_true", help="machine-readable result")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    if args.costs and len(args.costs) > 1:
        parser.error("at most one --costs file may be supplied")
    if args.files and args.pair:
        parser.error("use positional CNF pairs or --pair, not both")
    if len(args.files) % 2:
        parser.error("each A.cnf needs a corresponding B.cnf")
    paths = args.pair or list(zip(args.files[::2], args.files[1::2]))
    if not paths:
        parser.error("at least one CNF pair is required")
    try:
        pairs = [(read_dimacs(a), read_dimacs(b)) for a, b in paths]
        costs = read_costs(args.costs[0]) if args.costs else None
        result = select_variables(pairs, costs, solver=args.solver)
    except InfeasibleError as exc:
        if args.json:
            print(json.dumps({"status": "infeasible", "pair_index": exc.pair_index + 1,
                              "message": str(exc)}))
        else:
            print("s INFEASIBLE")
        print(f"min-cost-itp: {exc}", file=sys.stderr)
        return 2
    except (InputError, OSError, UnicodeError) as exc:
        print(f"min-cost-itp: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("min-cost-itp: interrupted; no optimum certified", file=sys.stderr)
        return 130
    except RuntimeError as exc:
        print(f"min-cost-itp: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"status": "optimal", **asdict(result)}, sort_keys=True))
    else:
        print("s OPTIMUM FOUND")
        print(f"o {result.min_cost}")
        print("v " + " ".join(map(str, (*result.selected_variables, 0))))
    return 0

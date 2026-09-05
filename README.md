# min-cost-itp

**Exact minimum-cost interpolation variable selection for one or more
inconsistent DIMACS CNF pairs.** Install the package, supply your formulas,
and change the variable costs to explore which interpolation support is cheapest.

The tool returns original variable IDs and their total minimum cost. It also
provides an in-memory Python API for use inside verification and synthesis
flows. It runs on PySAT's bundled CaDiCaL, Glucose, or MiniSat backends; ABC
and a separately installed SAT executable are unnecessary.

## Install and try

Requires Python 3.10 or newer. From this repository:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .

min-cost-itp examples/choice/choice_A.cnf examples/choice/choice_B.cnf
```

```text
s OPTIMUM FOUND
o 1
v 1 0
```

Here `A = x1 AND (x2 OR x3)` and `B = NOT x1 AND NOT x2 AND NOT x3`.
Either `{1}` or `{2, 3}` suffices. Unit costs select `{1}`. Make variable 1
expensive using the included cost file:

```sh
min-cost-itp examples/choice/choice_A.cnf examples/choice/choice_B.cnf --costs examples/choice/costs.txt
```

```text
s OPTIMUM FOUND
o 4
v 2 3 0
```

`python -m min_cost_itp` exposes the same interface. Use `--help` for options
and `--version` for the installed version. This project is installable from
the checkout or a built wheel; these instructions do not assume a published
package-index release.

PySAT is pinned to the version used for validation. Pip downloads its native
solver wheels where available; other platforms may need a C/C++ compiler to
build PySAT. Linux is covered by the included CI configuration.

For a larger input, see the [frogs unroll-8 example](examples/frogs.5.prop1-func-interl-k8/README.md):
it uses the 0818 fair-comparison cut at `s1`, with 261 shared variables, and
includes A/B DIMACS files, editable costs, signal names, and a verification script.

## Input contract

Each pair contains formulas `A` and `B` such that `A AND B` is UNSAT.
Both sides may contain private variables. A variable is shared when its
positive DIMACS ID occurs in clauses on both sides. Declaring an ID in the
header without using it does not make it a candidate. IDs must denote the
same logical variable wherever they are shared.

The parser accepts ordinary text DIMACS:

```text
c comments occupy a whole line
p cnf 3 2
1 0
2 3 0
```

There must be one `p cnf <variable-bound> <clause-count>` header. Clauses end
in zero and can span lines or share a line. `0` alone is an empty clause;
`p cnf 0 0` is the constant-true formula. Blank lines and whole-line `c`
comments are allowed, including between clause literals. Counts, bounds,
and terminators are checked. Inline comments, compression, and non-CNF
DIMACS extensions are unsupported. An individually UNSAT side is valid and
can make an empty support sufficient.

The optional cost file contains overrides:

```text
# variable cost
1 7
2 2
3 2
```

Costs must be **strictly positive integers**. Omitted candidates cost one.
Blank lines and whole-line `#` or `c` comments are allowed. Duplicate IDs,
nonpositive or fractional costs, and IDs not shared in any input pair are
errors. Integer costs use Python integers; they are not truncated to 32 bits.
To represent rational costs, scale them to positive integers first.

## Multiple pairs: one common minimum

Pass consecutive pairs or repeat `--pair`:

```sh
min-cost-itp \
  --pair examples/choice/choice_A.cnf examples/choice/choice_B.cnf \
  --pair examples/choice/force_A.cnf examples/choice/force_B.cnf \
  --costs examples/choice/costs.txt --json
```

The result selects `[1]` at cost `7`: the second pair requires variable 1,
which also suffices for the first. Optimizing pairs separately and taking
the union would instead select `{1,2,3}` at cost 11.

All pairs use a **common variable-ID namespace**. Candidates are the union
of the per-pair shared variables; each selected ID is charged once. An ID
only constrains pairs where it occurs on both sides. Private copies inside
each pair remain independent of other pairs. Renumber inputs first if their
ID meanings differ. To obtain independent minima, invoke the tool once per
pair. Positional pairs and `--pair` cannot be mixed in one invocation.

## Output and exit codes

Text output has three lines for a proven optimum:

- `s OPTIMUM FOUND`: the result is globally optimal.
- `o COST`: sum of selected variable costs.
- `v ID ... 0`: sorted positive original IDs, terminated by zero. This is a
  support set, not a satisfying assignment. An empty support is `v 0`.

`--json` emits one JSON object on stdout. Successful results contain:

| Field | Meaning |
| --- | --- |
| `status` | `optimal` |
| `selected_variables` | Sorted selected original IDs |
| `min_cost` | Exact total cost |
| `candidates` | Sorted union of shared IDs |
| `pair_count` | Number of pairs |
| `iterations` | Hitting-set candidates checked |
| `correction_sets` | Learned correction-set clauses |
| `sat_calls` | Pair-oracle calls, excluding internal optimization calls |

Statistics and the choice among tied optima may vary across solver versions.
No secondary tie-breaking objective is imposed.

| Exit code | Meaning |
| --- | --- |
| 0 | Proven optimum |
| 1 | Invalid file/data, I/O failure, or runtime failure |
| 2 | CLI usage error, or an infeasible (satisfiable) input pair |
| 130 | Keyboard interruption handled by Python |

An infeasible pair produces `s INFEASIBLE`, or a JSON object with
`status: "infeasible"`, a **one-based** `pair_index`, and a message. It has
no minimum-cost field. Usage errors produce no stdout. Diagnostics go to
stderr; errors never emit an uncertified optimum.

## Embed in an existing flow

```python
from min_cost_itp import CNF, select_variables

# Clauses contain signed literals without the DIMACS zero terminator.
a = CNF(((1,), (2, 3)), nvars=3)
b = CNF(((-1,), (-2,), (-3,)), nvars=3)
result = select_variables([(a, b)], costs={1: 7, 2: 2, 3: 2})
assert result.selected_variables == (2, 3)
assert result.min_cost == 4
```

Use `read_dimacs(path)` and `read_costs(path)` for file-based integrations.
`select_variables` accepts an iterable of CNF pairs and an optional cost
mapping. It returns an immutable `SelectionResult`. `InputError` signals
invalid arguments; `InfeasibleError.pair_index` identifies a satisfiable pair
using a **zero-based** index in the Python API. Solvers are released when the
call finishes or raises.

To integrate with an interpolation caller, pass its A/B clause partitions to
`select_variables`, then use `result.selected_variables` as the allowed
shared interface when constructing the interpolation query. Give each
unselected shared variable a fresh B-side ID in that query, leaving selected
IDs identified. Preserve a mapping back to your original signal names.
This selects the interface over which an interpolant exists; producing its
formula or proof remains the interpolation caller's responsibility.

This release supplies a support-selection CLI and API. Arbitrary SAT solver
executables have different partition/proof interfaces, so binary-compatible
replacement of an existing solver command is outside this interface. In a
flow that currently chooses shared variables by calling a SAT routine, the
Python API is the replacement point.

Choose the SAT backend for both pair queries and weighted optimization:

```sh
min-cost-itp examples/choice/choice_A.cnf examples/choice/choice_B.cnf --solver minisat22
```

The supported names are `cadical195` (default), `glucose3`, and `minisat22`.
In Python, pass `solver="glucose3"`. These backends support the incremental
assumptions and core queries needed by the search.

## Why the answer is a minimum

See [ALGORITHM.md](ALGORITHM.md) for the full encoding, pseudocode, and
correctness argument. The original solver defaults are retained; experimental
notes and measurements are under `benchmarks/`. Source snapshots are ignored.

For a proposed support `S`, build disjoint copies `A(x)` and `B(y)` and require
`x_v = y_v` for each shared `v` in `S`. The resulting formula is UNSAT exactly
when A's and B's satisfying assignments have disjoint projections onto `S`.
For propositional logic this is equivalent to the existence of an
interpolant `I(S)` with `A => I` and `I AND B` UNSAT. Unselected equalities
are removed, not assigned a Boolean value.

Each equality is encoded as two selector-guarded clauses. The SAT solver
retains the clauses and learned information across assumption queries.
The exact search then:

1. Checks that every pair is UNSAT with all its shared equalities enabled.
2. Uses weighted MaxSAT to find a minimum-cost hitting set of the correction
   sets learned so far. Initially the hitting set is empty.
3. Tests that support on every pair. If all are UNSAT, returns it.
4. For each SAT pair, greedily grows the selected equalities to a maximal
   satisfiable set and adds its complement as a new hitting-set constraint.
5. Repeats with the existing SAT and MaxSAT instances.

Any sufficient support must hit each learned complement: a support avoiding
it would be a subset of a satisfiable equality set. Thus the minimum hitting
set cost is a lower bound on every feasible support's cost. When that hitting
set is UNSAT for all pairs it is also feasible, proving equality with the
global optimum. Each failed candidate is excluded by a new constraint, so
the finite search terminates. Positive costs also make the result
subset-minimal, while the hitting-set optimization proves the stronger
minimum-cost property.

The algorithm follows the guarded-equality and implicit hitting-set design
of the ForMACE reference implementation, implemented independently of its
ABC-specific APIs. Weighted optimization uses
[PySAT's RC2](https://pysathq.github.io/docs/html/api/examples/rc2.html);
backend access uses the
[PySAT solver API](https://pysathq.github.io/docs/html/api/solvers.html).

## Development and limits

```sh
python -m pip install -e '.[dev]'
python -m pytest
python -m build
```

Tests include weighted tradeoffs, common supports, sparse IDs, private
variables, empty formulas, malformed input, CLI behavior, and independent
exhaustive model-projection/subset checks across all three backends. CI runs
the suite on Python 3.10, 3.12, and 3.14 and builds distributions. Source
distributions include examples and tests.

The search is exact and can take exponential time or learn many correction
sets. This initial standalone implementation does not include all reference
performance heuristics, a resource budget, an optimality proof file, or
interpolant construction. For long-running experiments, apply an external
process limit; a terminated run supplies no certified optimum. Python may
handle Ctrl-C only after an active native solver call returns. Large input
formulas and all pair solver instances reside in memory.

The project code is MIT-licensed; PySAT and its bundled solvers retain their
own licenses. See [LICENSE](LICENSE). The implementation plan and acceptance
checks are in [PLAN.md](PLAN.md).

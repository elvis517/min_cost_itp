# Frogs, unroll 8, first-transition cut

`A.cnf` and `B.cnf` encode `frogs.5.prop1-func-interl.aig` with the exact
partition options used by `try/tools/0818_fair_comparison/run_comparison.py`.
The cut is at **s1**, after the first transition:

```text
A = I(s0) AND T(s0,i0,s1)
B = T(s1,i1,s2) AND ... AND T(s7,i7,s8)
    AND (Bad(s1) OR ... OR Bad(s8))
```

Thus there are eight transitions in total. The bad-state check covers frames
1 through 8, with no frame-0 bad-state check. This is the `--bad-mode any`
partition, not a final-frame-only property check.

The source has 261 latches, 9 primary inputs per frame, 9,804 AND gates, one
bad property, and no constraints. `--property-source auto` selects that bad
property. The historical command does not enable `--include-constraints`;
there are no constraints to omit in this benchmark.

| Partition | Clauses | Used variables | DIMACS variable bound |
| --- | ---: | ---: | ---: |
| A | 33,322 | 11,638 | 89,472 |
| B | 227,833 | 78,095 | 89,472 |

The **261 shared variables are IDs 271–531**, exactly the `s1_` latch signals.
All other inputs and Tseitin variables have disjoint IDs between A and B.
Both headers use the same global bound; this does not make every declared
variable shared. CNF comments preserve the input signal-to-ID mapping.

Files:

- `A.cnf`, `B.cnf`: ready-to-use inconsistent pair.
- `shared_variables.txt`: original DIMACS IDs and boundary signal names.
- `costs.txt`: editable positive integer costs, initially all one.
- `provenance.json`: source/generator hashes, CNF hashes, and structural counts.
- `verify.py`: checks hashes, the shared namespace, A SAT, B SAT, and A AND B UNSAT.

Run from the repository root after installing the package:

```sh
python examples/frogs.5.prop1-func-interl-k8/verify.py
min-cost-itp \
  examples/frogs.5.prop1-func-interl-k8/A.cnf \
  examples/frogs.5.prop1-func-interl-k8/B.cnf \
  --costs examples/frogs.5.prop1-func-interl-k8/costs.txt --json
```

Omitting `--costs` gives the same unit-cost objective. The verification script
checks the partition's feasibility contract; it does not compute the minimum
support. This fixture is intended for harder experiments and is not part of
the fast unit-test suite.

## Reproduce the partition

From the ForMACE playground root, with the original benchmark and parser
tools available:

```sh
work=$(mktemp -d)
Verification_Tools/aiger/aigtoaig \
  try/benchmarks/beem/frogs.5.prop1-func-interl.aig "$work/source.aag"
python3 try/tools/parsers/split_bmc_aag.py "$work/source.aag" -k 8 \
  --a-out "$work/A.aag" --b-out "$work/B.aag" \
  --property-source auto --bad-mode any
python3 try/tools/parsers/aag_pair_to_cnf.py "$work/A.aag" "$work/B.aag" \
  --a-out "$work/A.cnf" --b-out "$work/B.cnf" --shared-prefix s1_
```

Regeneration was checked against the archived frogs k8 pairs in both
`try/results/0818_ablation/abc_api/inputs/frogs.5.prop1-func-interl/k8` and
`try/results/0819_fair_comparison/frogs.5.prop1-func-interl/inputs/k8`.
DIMACS headers and every clause match exactly. The first comment line in
the distributed files was replaced with portable benchmark/cut metadata,
so full-file hashes differ from the historical files. No clauses or variable
IDs were changed.

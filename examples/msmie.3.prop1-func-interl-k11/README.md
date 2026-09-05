# MSMIE, unroll 11, first-transition cut

This is `msmie.3.prop1-func-interl` at depth 11, using the same 0818
fair-comparison options as the frogs example:

```text
A = I(s0) AND T(s0,i0,s1)
B = T(s1,i1,s2) AND ... AND T(s10,i10,s11)
    AND (Bad(s1) OR ... OR Bad(s11))
```

The **153 shared variables are IDs 405–557**, the `s1_` latch boundary.
The source has 251 primary inputs, 153 latches, 4,224 AND gates, and one bad
property. A has 14,962 clauses; B has 145,114. Both DIMACS headers use the
global variable bound 57,955. The actual used-variable counts are 5,544 and
52,564, respectively.

The headers and every clause were regenerated and compared with
`try/results/0819_fair_comparison/msmie.3.prop1-func-interl/inputs/k11`.
Only the generated-path comment was replaced with portable metadata.
`provenance.json` contains hashes and counts; `shared_variables.txt` maps
IDs to signals; `costs.txt` starts with unit costs.

From the repository root after installation:

```sh
min-cost-itp examples/msmie.3.prop1-func-interl-k11/A.cnf \
  examples/msmie.3.prop1-func-interl-k11/B.cnf --json
```

The unchanged standalone baseline computed minimum cardinality **39** in the
2026-09-05 experiment. See the benchmark report for current runtimes, machine
conditions, and comparisons; historical timings are not directly comparable.

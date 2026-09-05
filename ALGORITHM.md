# Exact minimum-cost interpolation support

This document describes the implemented optimization problem and why the
search is exact. The source is `src/min_cost_itp/solver.py`. The original default implementation
was restored after the 2026-09-05 experiments. Experimental notes and measurements are kept
under `benchmarks/`; source snapshots are local ignored files and are not used
by the CLI or Python API.

## 1. What is being minimized?

For each input pair `(A_j, B_j)`, let `V_j` contain the variable IDs occurring
in both formulas. Candidates are `V = union_j V_j`. Each candidate `v` has a
strictly positive integer cost `w_v`, defaulting to one.

We seek a single set `S ⊆ V` minimizing

```text
cost(S) = sum(w_v for v in S)
```

such that an interpolant over `S ∩ V_j` exists for every pair. A variable is
charged once across all pairs. IDs must have consistent meanings across pairs;
the private variables and models of different pairs remain independent.

This is global minimum cost, not just deletion-minimality. A deletion-minimal
support has no removable element but can still cost more than another support.
With unit costs our objective is minimum cardinality. No interpolant or
resolution proof is constructed by this package.

## 2. Reduce support feasibility to incremental SAT

Give A and B disjoint private copies of every variable, including their shared
variables. For each shared ID `v`, introduce a private selector `e_v` guarding
the equality of its two copies:

```text
(-e_v OR -a_v OR b_v)
(-e_v OR  a_v OR -b_v)
```

The background formula is `A(a) AND B(b)`. To check support `S`, solve with
positive assumptions `e_v` for `v ∈ S ∩ V_j`. Omitted selectors are free to be
false, so no omitted equality is required. Original variables are densely
renumbered internally, while results retain the caller's original IDs.

Define this oracle formula as `Q_j(S)`. Then:

- `Q_j(S)` SAT means A and B have models agreeing on all selected variables.
  Such a support cannot distinguish those models.
- `Q_j(S)` UNSAT means their projections onto the selected variables are
  disjoint. The projection of A itself defines a possible interpolant over
  those variables: A implies it, and it is inconsistent with B.

Consequently, `S` is feasible exactly when **every** `Q_j(S)` is UNSAT. This
predicate is monotone: adding equalities preserves UNSAT; removing them
preserves SAT. A satisfiable original `A_j AND B_j` is rejected before search.
If the hard background already contradicts itself, that pair needs no shared
variables; if this holds for all pairs, the global optimum is the empty set.

Each pair owns one incremental SAT solver. Its clauses and learned information
persist through feasibility checks and correction-set discovery.

## 3. Learn necessary conditions from counterexamples

Suppose `Q_j(S)` is SAT. Let `M` be any larger set of that pair's shared
equalities that is still SAT. Its complement

```text
C = V_j \ M
```

is a correction set. Every feasible global support must include at least one
member of C. Otherwise its equalities for pair j would be a subset of M and
would remain satisfiable. This yields the hard hitting-set clause

```text
OR(y_v for v in C)
```

where `y_v` means that original variable v is selected globally.

Maximal growth is optional. A maximal satisfiable equality set gives a
minimal correction set, which usually produces a stronger clause. A smaller
proven-SAT set gives a weaker but still sound clause. Since M includes the
failed candidate, the new clause excludes that candidate and ensures progress.

The implementation grows M one equality at a time. Starting with the failed
candidate's local equalities, it tries every remaining shared variable in
ascending ID order. If adding that equality preserves SAT, it keeps it;
otherwise, it skips it. Once an equality fails, later additions cannot make it
satisfiable, by monotonicity. Therefore one pass suffices to reach an MSS.
Its complement is a minimal correction set. This can require one SAT query
per remaining variable; it is the main measured bottleneck on the examples.

The active implementation does not absorb additional equalities from models,
cache assumption cores, or apply experimental growth budgets.

## 4. Optimize the learned hitting-set problem

The map solver is RC2 weighted MaxSAT over one Boolean `y_v` per candidate:

- Hard clauses require hitting each learned correction set.
- Soft clauses `(-y_v)` with weight `w_v` penalize selecting v.

Minimizing unsatisfied soft weight therefore minimizes support cost. The RC2
instance is retained as hard clauses are added; we do not enumerate all
supports or all correction sets in advance.

```text
validate full support for every pair
H := empty collection of correction sets
repeat:
    S := exact minimum-cost hitting set of H
    for each pair j:
        if Q_j(S) is SAT:
            M := grow S using only certified SAT information
            add V_j \ M to H
    if every pair was UNSAT:
        return S and cost(S)
```

Every feasible support satisfies all clauses in H, so the optimum map cost is
a lower bound on the true optimum. When the map's support is itself feasible,
it supplies a matching upper bound. Thus the result is globally optimal.
Each failed candidate is excluded, and the candidate universe is finite, so
the exact loop terminates absent resource exhaustion.

## 5. Exact stopping rule and implementation scope

The active search returns only when the exact minimum hitting set is UNSAT
in every pair. It does not stop from experimental incumbent/core bounds.
All candidates remain available throughout the search. With positive costs,
the resulting minimum-cost support is also subset-minimal.

SAT backends are CaDiCaL 1.9.5 (default), Glucose 3, and MiniSat 2.2 through
PySAT. The same chosen backend supports the pair oracles and RC2. Files are
parsed before solver construction; native instances are released on return
or exception. There is no built-in runtime budget or proof-file output.
Resource-limited experiments use BenchExec outside the package; a timed-out
run reports no optimum.

The growth experiments and their rationale are recorded in
[experimental notes](benchmarks/EXPERIMENTAL_ALGORITHMS.md). Their source snapshots are local ignored files; no experimental code is
part of the installed package.

## 6. Sources and further reading

The implicit hitting-set scheme, disjoint corrections, and the use of a
feasible upper bound are established techniques in smallest-UNSAT-subset
optimization. See Ignatiev, Previti, Liffiton, and Marques-Silva,
[Smallest MUS Extraction with Minimal Hitting Set Dualization](https://alexeyignatiev.github.io/assets/pdf/iplms-cp15-preprint.pdf),
CP 2015, especially Sections 3–4. The local papers collection contains this
paper under `papers/minunsat/smallest_mus/`.

Model growth and the tradeoff between cheap correction sets and stronger,
more expensive growth are discussed in Gamba, Bogaerts, and Guns,
[Efficiently Explaining CSPs with Unsatisfiable Subset Optimization](https://arxiv.org/abs/2303.11712),
Section 5.3. The archived equality-value absorption and bounded-growth experiments
specialize those ideas to this package's paired-CNF oracle.

The grouped-disjunction experiment follows the clause-D idea from
Marques-Silva, Heras, Janota, Previti, and Belov,
[On Computing Minimal Correction Subsets](https://www.ijcai.org/Proceedings/13/Papers/098.pdf),
IJCAI 2013. It was evaluated separately; the experiment did not change the default.

The ForMACE reference implementation provides the guarded-group setting and
related search heuristics. This package implements the selection layer
independently of ABC. The search remains exponential in the worst case;
improvements to growth and bounds change practical behavior, not that limit.

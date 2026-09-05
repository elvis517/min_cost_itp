# Standalone minimum-cost interpolation support

## Contract

Accept one or more `(A, B)` DIMACS CNF pairs and at most one optional text
cost file. Return a globally minimum-cost set of original variable IDs that
supports an interpolant for every pair, and its cost. Variable IDs have the
same meaning across pairs. Candidates are the union of per-pair shared
variables; selected IDs absent from a pair's shared variables have no effect
on that pair. Charge each selected ID once. Default costs are one; overrides
are strictly positive integers. Report a satisfiable pair as infeasible.

The tool selects variables; it does not construct an interpolant or pretend
to implement a proof-producing solver's command-line protocol.

## Implementation sequence

1. Provide an installable Python package, CLI, and in-memory API using PySAT
   SAT backends and RC2 weighted optimization, independent of ABC.
2. Parse DIMACS strictly, including empty clauses and multiline clauses;
   validate cost IDs, duplicate entries, bounds, and positive integers.
3. Give A and B disjoint private copies of all variables. Guard the equality
   of each shared variable with a selector. A selected support is sufficient
   exactly when the guarded formula under those selectors is UNSAT.
4. Compute exact weighted hitting sets of learned correction sets. Check
   each candidate against every pair. Grow a satisfiable candidate to a
   maximal satisfiable equality set and learn its complement. Reuse the SAT
   and optimization instances. Return only after all pairs are UNSAT.
5. Document input/output, mathematical semantics and optimality, backend
   selection, integration, examples, failure modes, and practical limits.
6. Verify with exhaustive truth-table projection and subset enumeration on
   small generated formulas, cross-backend tests, CLI failures, examples,
   and installation from a built distribution outside this checkout.

## Completion checks

- Single and multiple pairs; weighted and default unit costs.
- One set across pairs, with cost counted once; local and sparse IDs.
- Satisfiable input rejected, empty support handled, strict malformed input.
- Exact optimum independently checked, rather than merely subset-minimality.
- README, ignore rules, license, examples, CI, distributable package and API.
- No dependency on this workspace, ABC, or a separately installed solver.

## Design rationale

The reference implementation establishes the guarded-equality and implicit
hitting-set approach. This implementation expresses that same exact search
using maintained solver bindings instead of copying ABC-specific allocation,
vector, and proof interfaces. PySAT provides selectable incremental SAT
backends; RC2 provides weighted hitting-set optimization without a bespoke
pseudo-Boolean encoder. The initial release prioritizes a small, testable
integration surface. It does not port every reference search heuristic.

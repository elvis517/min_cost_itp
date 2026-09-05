"""Independent semantic checks: enumerate models and project onto supports."""

from itertools import combinations, product
import random

import pytest

from min_cost_itp import BACKENDS, CNF, InfeasibleError, InputError, select_variables


def cnf(clauses, nvars=3):
    return CNF(tuple(tuple(c) for c in clauses), nvars)


def models(formula):
    variables = sorted(formula.variables)
    return [dict(zip(variables, bits)) for bits in product((False, True), repeat=len(variables))
            if all(any(dict(zip(variables, bits))[abs(l)] == (l > 0) for l in clause)
                   for clause in formula.clauses)]


def feasible_support(a, b, support):
    shared = sorted(a.variables & b.variables & set(support))
    left = {tuple(m[v] for v in shared) for m in models(a)}
    right = {tuple(m[v] for v in shared) for m in models(b)}
    return left.isdisjoint(right)


def brute_minimum(pairs, costs):
    universe = sorted(set().union(*(a.variables & b.variables for a, b in pairs)))
    best = None
    for size in range(len(universe) + 1):
        for selected in combinations(universe, size):
            if all(feasible_support(a, b, selected) for a, b in pairs):
                cost = sum(costs.get(v, 1) for v in selected)
                best = cost if best is None else min(best, cost)
    return best


TRADEOFF = (cnf([[1], [2, 3]]), cnf([[-1], [-2], [-3]]))


@pytest.mark.parametrize("backend", BACKENDS)
def test_weighted_and_common(backend):
    result = select_variables([TRADEOFF], solver=backend)
    assert result.selected_variables == (1,)
    assert result.min_cost == 1
    costs = {1: 7, 2: 2, 3: 2}
    result = select_variables([TRADEOFF], costs, solver=backend)
    assert result.selected_variables == (2, 3)
    assert result.min_cost == 4
    # Joint optimization must reconsider the first pair's individual optimum.
    result = select_variables([TRADEOFF, (cnf([[1]]), cnf([[-1]]))], costs, solver=backend)
    assert result.selected_variables == (1,)
    assert result.min_cost == 7


@pytest.mark.parametrize("backend", BACKENDS)
def test_empty_support_and_no_variables(backend):
    for a, b in [(cnf([[]], 0), cnf([], 0)), (cnf([[1], [-1]]), cnf([[1]]))]:
        result = select_variables([(a, b)], solver=backend)
        assert result.selected_variables == ()
        assert result.min_cost == 0
    with pytest.raises(InfeasibleError):
        select_variables([(cnf([], 0), cnf([], 0))], solver=backend)


@pytest.mark.parametrize("backend", BACKENDS)
def test_local_variables_and_sparse_namespaces(backend):
    big = 10**9
    a = cnf([[big, 17], [big, -17]], big)
    b = cnf([[-big, 51], [-big, -51]], big)
    pair2 = (cnf([[7]], big), cnf([[-7]], big))
    result = select_variables([(a, b), pair2], {big: 10**30, 7: 3}, solver=backend)
    assert result.candidates == (7, big)
    assert result.selected_variables == (7, big)
    assert result.min_cost == 10**30 + 3


@pytest.mark.parametrize("backend", BACKENDS)
def test_infeasible_pair_index(backend):
    with pytest.raises(InfeasibleError) as caught:
        select_variables([TRADEOFF, (cnf([[1]]), cnf([[2]]))], solver=backend)
    assert caught.value.pair_index == 1


@pytest.mark.parametrize("costs", [{1: 0}, {1: -1}, {1: 1.5}, {1: True}, {99: 2}, {True: 1}])
def test_invalid_api_costs(costs):
    with pytest.raises(InputError):
        select_variables([TRADEOFF], costs)


def test_invalid_api_inputs():
    with pytest.raises(InputError):
        select_variables([])
    with pytest.raises(InputError):
        select_variables([TRADEOFF], solver="unknown")
    with pytest.raises(InputError):
        select_variables([(cnf([]), "not a formula")])
    for clauses, bound in [([[0]], 1), ([[2]], 1), ([[True]], 1), ([], -1)]:
        with pytest.raises(InputError):
            cnf(clauses, bound)


@pytest.mark.parametrize("backend", BACKENDS)
def test_generated_formulas_against_exhaustive_projection(backend):
    rng = random.Random(84921)
    for case in range(100):
        nvars = rng.randint(1, 4)

        def generated():
            return cnf([[rng.choice((-1, 1)) * rng.randint(1, nvars)
                         for _ in range(rng.randint(1, 3))]
                        for _ in range(rng.randint(0, 6))], nvars)

        pairs = [(generated(), generated()) for _ in range(1 + case % 3)]
        universe = set().union(*(a.variables & b.variables for a, b in pairs))
        costs = {v: rng.randint(1, 9) for v in universe} if case % 2 else {}
        expected = brute_minimum(pairs, costs)
        if expected is None:
            with pytest.raises(InfeasibleError):
                select_variables(pairs, costs, solver=backend)
        else:
            result = select_variables(pairs, costs, solver=backend)
            assert result.min_cost == expected, (case, pairs, costs, result)
            assert all(feasible_support(a, b, result.selected_variables) for a, b in pairs)


@pytest.mark.parametrize("backend", BACKENDS)
def test_generated_feasible_relations(backend):
    # Exclude complementary halves of the Boolean cube. These pairs are
    # guaranteed inconsistent, while individual sides remain satisfiable.
    rng = random.Random(147)
    for _ in range(35):
        nvars = 4
        pairs = []
        for _ in range(rng.randint(1, 3)):
            left, right = [], []
            for bits in product((False, True), repeat=nvars):
                blocking = [-(i + 1) if bit else i + 1 for i, bit in enumerate(bits)]
                (left if rng.getrandbits(1) else right).append(blocking)
            pairs.append((cnf(left, nvars), cnf(right, nvars)))
        costs = {v: rng.randint(1, 12) for v in range(1, nvars + 1)}
        result = select_variables(pairs, costs, solver=backend)
        assert result.min_cost == brute_minimum(pairs, costs)
        assert all(feasible_support(a, b, result.selected_variables) for a, b in pairs)

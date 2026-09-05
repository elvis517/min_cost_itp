"""Run with: python examples/use_api.py"""

from min_cost_itp import CNF, select_variables

a = CNF(((1,), (2, 3)), nvars=3)
b = CNF(((-1,), (-2,), (-3,)), nvars=3)
result = select_variables([(a, b)], costs={1: 7, 2: 2, 3: 2})
print("Selected variables:", result.selected_variables)
print("Minimum cost:", result.min_cost)

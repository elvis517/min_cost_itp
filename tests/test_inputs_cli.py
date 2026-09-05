import json
from pathlib import Path
import subprocess
import sys

import pytest

from min_cost_itp import InputError, parse_dimacs, read_costs

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def parse(text):
    return parse_dimacs(text.splitlines())


def test_dimacs_multiline_comments_and_empty_clause():
    result = parse("c example\np cnf 4 3\n1\nc between literals\n-2 0 3 0\n0\n")
    assert result.clauses == ((1, -2), (3,), ())
    assert result.variables == {1, 2, 3}
    assert parse("p cnf 0 0").clauses == ()


@pytest.mark.parametrize("text", [
    "", "1 0", "p cnf 1 1\n2 0", "p cnf 1 1\n1", "p cnf 1 0\n0",
    "p cnf -1 0", "p cnf 1 1", "p cnf x 0", "p cnf 1 1\na 0",
    "p cnf 1 0\np cnf 1 0", "p dnf 1 0", "p cnf 1 1\n1 0 c trailing",
])
def test_bad_dimacs(text):
    with pytest.raises(InputError):
        parse(text)


@pytest.mark.parametrize("text", ["1 0", "1 -2", "1 1.5", "1 2\n1 3", "0 2", "1", "1 2 extra"])
def test_bad_costs(tmp_path, text):
    path = tmp_path / "costs.txt"
    path.write_text(text)
    with pytest.raises(InputError):
        read_costs(path)


def test_cost_comments(tmp_path):
    path = tmp_path / "costs.txt"
    path.write_text("# cost overrides\nc comment\n\n1 7\n2 2\n")
    assert read_costs(path) == {1: 7, 2: 2}


def run(*args):
    return subprocess.run([sys.executable, "-m", "min_cost_itp", *map(str, args)],
                          capture_output=True, text=True, timeout=20)


def test_cli_text_and_json():
    pair = [EXAMPLES / "choice_A.cnf", EXAMPLES / "choice_B.cnf"]
    result = run(*pair)
    assert result.returncode == 0
    assert result.stdout == "s OPTIMUM FOUND\no 1\nv 1 0\n"
    assert result.stderr == ""
    result = run(*pair, "--costs", EXAMPLES / "costs.txt", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "optimal"
    assert data["selected_variables"] == [2, 3]
    assert data["min_cost"] == 4


def test_cli_multiple_pairs():
    pairs = [EXAMPLES / name for name in ("choice_A.cnf", "choice_B.cnf", "force_A.cnf", "force_B.cnf")]
    for args in (pairs, ["--pair", *pairs[:2], "--pair", *pairs[2:]]):
        result = run(*args, "--costs", EXAMPLES / "costs.txt", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert (data["selected_variables"], data["min_cost"], data["pair_count"]) == ([1], 7, 2)


def test_cli_empty_and_infeasible(tmp_path):
    a, b = tmp_path / "a.cnf", tmp_path / "b.cnf"
    a.write_text("p cnf 0 1\n0\n")
    b.write_text("p cnf 0 0\n")
    result = run(a, b)
    assert result.returncode == 0
    assert result.stdout == "s OPTIMUM FOUND\no 0\nv 0\n"
    a.write_text("p cnf 0 0\n")
    result = run(a, b, "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "infeasible"
    assert "min_cost" not in json.loads(result.stdout)


@pytest.mark.parametrize("args", [[], ["a"], ["--pair", "a"], ["a", "b", "--pair", "c", "d"],
                                   ["a", "b", "--costs", "c", "--costs", "d"],
                                   ["--solver", "unknown", "a", "b"]])
def test_cli_bad_usage(args):
    result = run(*args)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr


def test_cli_input_error(tmp_path):
    result = run(tmp_path / "missing", tmp_path / "also-missing", "--json")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    bad = tmp_path / "bad.cnf"
    bad.write_text("p cnf 1 1\n2 0")
    result = run(bad, bad)
    assert result.returncode == 1
    assert "exceeds" in result.stderr

import ast
from pathlib import Path

from vks import heldout

SRC = Path(__file__).resolve().parents[1] / "src" / "vks"


def test_search_and_agents_never_name_the_truth():
    for part in ("search", "agents"):
        for f in (SRC / part).rglob("*.py"):
            text = f.read_text()
            for word in ("truth", "evalcases", "queries_heldout"):
                assert word not in text, f"{f.name} mentions {word}"


def test_search_and_agents_never_import_the_evaluation():
    for part in ("search", "agents"):
        for f in (SRC / part).rglob("*.py"):
            for node in ast.walk(ast.parse(f.read_text())):
                if isinstance(node, ast.ImportFrom):
                    assert not (node.module or "").startswith("vks.evals"), f.name


def test_monitors_and_mining_read_only_the_log():
    for name, body_of in (("monitor.py", None), ("production.py", "def mine")):
        src = (SRC / "evals" / name).read_text()
        body = src if body_of is None else src[src.index(body_of) : src.index("def replay")]
        assert "truth" not in body and "labelled(" not in body


def test_the_held_out_data_is_what_was_pinned():
    assert heldout.fingerprint() == heldout.pinned()

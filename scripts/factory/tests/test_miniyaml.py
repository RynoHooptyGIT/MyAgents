import pytest

from .. import miniyaml


def test_nested_map_and_list():
    doc = miniyaml.parse('a: 1\nb:\n  c: "x y"\n  d:\n    - "**/z"\n    - plain\ne: 2.5  # note\nf: true\n')
    assert doc == {"a": 1, "b": {"c": "x y", "d": ["**/z", "plain"]}, "e": 2.5, "f": True}


def test_comments_and_blank_lines_and_hash_in_quotes():
    assert miniyaml.parse('# top\n\nk: "a # b"\n') == {"k": "a # b"}


def test_empty_containers():
    assert miniyaml.parse("a: []\nb: {}\n") == {"a": [], "b": {}}


@pytest.mark.parametrize("text", [
    "a: 1\na: 2\n",            # duplicate key
    "a:\n\tb: 1\n",            # tab
    "a: 1\n  b: 2\n",          # unexpected indent
    "a: [1, 2]\n",             # flow sequence unsupported
    "- x\nb: 1\n",             # mixed list and map
    "just text\n",             # no colon
    'a: "unterminated\n',
    "a:\n",                    # key with no value and no children
    "a:\n  - x\n - y\n",       # bad indent
])
def test_malformed_rejected(text):
    with pytest.raises(miniyaml.YamlError):
        miniyaml.parse(text)


def test_matches_pyyaml_on_shipped_policy():
    yaml = pytest.importorskip("yaml")
    from pathlib import Path
    p = Path(__file__).resolve().parents[3] / ".factory" / "policy.yaml"
    assert miniyaml.parse(p.read_text()) == yaml.safe_load(p.read_text())

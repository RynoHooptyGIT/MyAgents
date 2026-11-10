import pytest

from .. import classifier as c
from .. import policy as pol
from pathlib import Path

POLICY = pol.load(Path(__file__).resolve().parents[3])


def cls(paths, added=5, deleted=0, deleted_files=0, new_dep=False, verdict="agree",
        sealed=0, exhausted=False, budget=False, level="T1"):
    return c.classify(POLICY, paths, added, deleted, deleted_files, new_dep, verdict,
                      sealed, exhausted, budget, level)


# ---- globs ----
@pytest.mark.parametrize("pat,path,expected", [
    ("scripts/factory/**", "scripts/factory/x.py", True),
    ("scripts/factory/**", "scripts/factory/a/b/c.py", True),
    ("scripts/factory/**", "scripts/factory", False),
    ("scripts/factory/**", "scripts/factoryx/a.py", False),
    ("scripts/factory/**", "other/scripts/factory/a.py", False),
    (".github/**", ".github/workflows/ci.yml", True),
    (".claude/settings*", ".claude/settings.json", True),
    (".claude/settings*", ".claude/settings.local.json", True),
    (".claude/settings*", ".claude/sub/settings.json", False),
    ("**/CLAUDE.md", "CLAUDE.md", True),
    ("**/CLAUDE.md", "a/b/CLAUDE.md", True),
    ("**/CLAUDE.md", "a/NOTCLAUDE.md", False),
    ("**/*secret*", "config/my_Secret_file.txt", True),
    ("**/*secret*", "secrets.yaml", True),
    ("**/*secret*", "secret/readme.md", False),   # '*' does not cross '/', dir name not matched
    ("**/.env.*", "app/.env.prod", True),
    ("**/.env", ".env", True),
    ("*.md", "a/b.md", False),
    ("*.md", "b.md", True),
    ("a?c", "abc", True),
    ("a?c", "a/c", False),
    ("a/**/b", "a/b", True),
    ("a/**/b", "a/x/y/b", True),
    ("a/**/b", "ab", False),
    ("a.b", "aXb", False),             # regex metachar is literal
    ("a[1]", "a1", False),             # brackets literal
    ("a[1]", "a[1]", True),
])
def test_glob(pat, path, expected):
    assert c.glob_match(pat, path) is expected


@pytest.mark.parametrize("raw,norm", [
    ("./a/b.py", "a/b.py"),
    ("a//b.py", "a/b.py"),
    ("a\\b.py", "a/b.py"),
    ("a/./b/../c.py", "a/c.py"),
    ("/abs/x.py", None),
    ("../escape.py", None),
    ("a/../../x", None),
    ("", None),
])
def test_normalize(raw, norm):
    assert c.normalize_path(raw) == norm


# ---- tiers ----
def test_docs_only_is_t0():
    r = cls(["docs/a.md", "README.md"])
    assert r.tier == "T0"


def test_tests_only_is_t0():
    assert cls(["scripts/x/tests/test_a.py"]).tier == "T0"


def test_ordinary_change_is_t1_when_verifier_agrees():
    assert cls(["skills/a/b.py"]).tier == "T1"


def test_ordinary_change_without_agreement_is_t2():
    for v in ("disagree", "not_run", None):
        r = cls(["skills/a/b.py"], verdict=v)
        assert r.tier == "T2" and r.reasons


def test_t0_does_not_need_verifier():
    assert cls(["docs/a.md"], verdict="not_run").tier == "T0"


def test_verifier_disagreement_forces_t2_even_for_docs():
    assert cls(["docs/a.md"], verdict="disagree").tier == "T2"


@pytest.mark.parametrize("path", [
    "scripts/factory/runner.py", ".factory/policy.yaml", ".github/workflows/x.yml",
    ".claude/settings.json", ".agents/hooks/a.sh", "team/engine/e.py", "CLAUDE.md",
    "docs/CLAUDE.md", "docs/my-credentials.md", "app/.env", "keys/server.pem",
    "SCRIPTS/FACTORY/x.py",   # case-insensitive
])
def test_protected_always_t2_even_at_earned_t1(path):
    r = cls([path, "docs/a.md"])
    assert r.tier == "T2"
    assert any("protected" in x for x in r.reasons)


def test_protected_beats_traversal_tricks():
    assert cls(["docs/../scripts/factory/runner.py"]).tier == "T2"
    assert cls(["./scripts/factory/runner.py"]).tier == "T2"
    assert cls(["scripts\\factory\\runner.py"]).tier == "T2"


def test_unnormalizable_path_is_t2():
    for bad in ("../x", "/etc/passwd", ""):
        r = cls([bad, "docs/a.md"])
        assert r.tier == "T2"


def test_new_dependency_t2():
    assert cls(["skills/a.py"], new_dep=True).tier == "T2"


def test_dependency_file_path_counts_as_new_dependency():
    r = cls(["app/requirements-dev.txt"], new_dep=False)
    assert r.tier == "T2"


def test_size_cap_boundary():
    cap = POLICY.max_diff_lines
    assert cls(["skills/a.py"], added=cap - 10, deleted=10).tier == "T1"
    assert cls(["skills/a.py"], added=cap - 9, deleted=10).tier == "T2"
    assert cls(["docs/a.md"], added=cap + 1).tier == "T2"


def test_deleted_files_cap_boundary():
    cap = POLICY.max_deleted_files
    assert cls(["skills/a.py"], deleted_files=cap).tier == "T1"
    assert cls(["skills/a.py"], deleted_files=cap + 1).tier == "T2"


@pytest.mark.parametrize("kw", [dict(sealed=1), dict(exhausted=True), dict(budget=True)])
def test_other_t2_triggers(kw):
    assert cls(["docs/a.md"], **kw).tier == "T2"


def test_earned_level_t2_floors_everything():
    r = cls(["docs/a.md"], level="T2")
    assert r.tier == "T2"
    assert any("earned" in x for x in r.reasons)


def test_all_reasons_listed_and_highest_wins():
    r = cls(["scripts/factory/a.py"], added=900, new_dep=True, verdict="disagree",
            sealed=2, exhausted=True, budget=True, deleted_files=99, level="T2")
    assert r.tier == "T2"
    assert len(r.reasons) >= 8


def test_t2_reasons_empty_for_clean_t0_t1():
    assert cls(["docs/a.md"]).reasons == []
    assert cls(["skills/a.py"]).reasons == []


def test_mixed_docs_and_code_is_not_t0():
    assert cls(["docs/a.md", "skills/a.py"]).tier == "T1"


@pytest.mark.parametrize("kw", [
    dict(paths=[]), dict(added=-1), dict(deleted=-1), dict(deleted_files=-1), dict(sealed=-1),
    dict(level="T3"), dict(verdict="maybe"), dict(added=True), dict(sealed=1.5),
])
def test_invalid_input_raises(kw):
    args = dict(paths=["docs/a.md"])
    args.update(kw)
    with pytest.raises(ValueError):
        cls(**args)


def test_category_single_top_level():
    assert c.category(["skills/a/x.py", "skills/b.md"]) == "skills"


def test_category_mixed_and_root():
    assert c.category(["skills/a.py", "docs/b.md"]) == "mixed"
    assert c.category(["README.md"]) == "root"


def test_secret_directories_protected():
    assert cls(["config/secrets/prod.yaml"]).tier == "T2"
    assert cls(["credentials/a.json"]).tier == "T2"

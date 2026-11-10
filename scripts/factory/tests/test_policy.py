import copy
from pathlib import Path

import pytest

from .. import miniyaml, policy

REPO = Path(__file__).resolve().parents[3]
GOOD = (REPO / ".factory" / "policy.yaml").read_text()


def _dump_variant(mutate):
    data = copy.deepcopy(miniyaml.parse(GOOD))
    mutate(data)
    return data


def test_shipped_policy_loads_with_design_defaults():
    p = policy.load(REPO)
    assert p.promotion_count == 5
    assert "scripts/factory/**" in p.protected_paths
    assert p.routing["build"] == "sonnet"
    assert p.routing["verifier"] == "opus"
    assert p.routing["retry_round_2"] == "fable"
    assert p.max_awaiting_human >= 1
    assert p.per_issue_usd > 0 and p.per_day_usd >= p.per_issue_usd
    assert "RynoHooptyGIT" in p.allowlisted_authors


def test_missing_policy_is_error(tmp_path):
    with pytest.raises(policy.PolicyError, match="missing"):
        policy.load(tmp_path)


def test_malformed_policy_is_error(tmp_path):
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "policy.yaml").write_text("a: [1\n")
    with pytest.raises(policy.PolicyError):
        policy.load(tmp_path)


def test_empty_policy_is_error(tmp_path):
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "policy.yaml").write_text("# nothing\n")
    with pytest.raises(policy.PolicyError):
        policy.load(tmp_path)


def test_unknown_key_rejected():
    with pytest.raises(policy.PolicyError, match="unknown"):
        policy.from_dict(_dump_variant(lambda d: d.update(bogus=1)))


@pytest.mark.parametrize("path,value", [
    (("size", "max_diff_lines"), 0),
    (("size", "max_diff_lines"), "big"),
    (("size", "max_deleted_files"), -1),
    (("autonomy", "promotion_count"), 0),
    (("autonomy", "promotion_count"), True),
    (("budget", "per_issue_usd"), 0),
    (("budget", "per_day_usd"), -3),
    (("queue", "max_awaiting_human"), 0),
    (("retries", "max_rounds"), 3),
    (("allowlisted_authors",), []),
    (("allowlisted_authors",), "bob"),
    (("protected_paths",), []),
    (("version",), 2),
])
def test_bad_values_rejected(path, value):
    def mutate(d):
        cur = d
        for k in path[:-1]:
            cur = cur[k]
        cur[path[-1]] = value
    with pytest.raises(policy.PolicyError):
        policy.from_dict(_dump_variant(mutate))


@pytest.mark.parametrize("key", ["routing", "budget", "size", "autonomy", "queue", "retries",
                                 "protected_paths", "allowlisted_authors", "t0_paths",
                                 "dependency_files", "tiers", "version"])
def test_missing_section_rejected(key):
    with pytest.raises(policy.PolicyError, match=key):
        policy.from_dict(_dump_variant(lambda d: d.pop(key)))


def test_missing_role_rejected():
    with pytest.raises(policy.PolicyError, match="verifier"):
        policy.from_dict(_dump_variant(lambda d: d["routing"].pop("verifier")))


def test_verifier_must_differ_from_builder():
    with pytest.raises(policy.PolicyError, match="verifier"):
        policy.from_dict(_dump_variant(lambda d: d["routing"].update(verifier="sonnet")))


def test_retry_round_2_must_differ_from_builder():
    with pytest.raises(policy.PolicyError, match="retry_round_2"):
        policy.from_dict(_dump_variant(lambda d: d["routing"].update(retry_round_2="sonnet")))


def test_cannot_unprotect_factory_or_policy():
    for needed in ("scripts/factory/**", ".factory/policy.yaml"):
        with pytest.raises(policy.PolicyError, match="protected"):
            policy.from_dict(_dump_variant(
                lambda d: d.update(protected_paths=[x for x in d["protected_paths"] if x != needed])))


def test_per_issue_cannot_exceed_per_day():
    with pytest.raises(policy.PolicyError, match="per_issue"):
        policy.from_dict(_dump_variant(lambda d: d["budget"].update(per_issue_usd=100.0, per_day_usd=10.0)))

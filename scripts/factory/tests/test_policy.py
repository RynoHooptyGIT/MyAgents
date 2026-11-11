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
                                 "dependency_files", "tiers", "version", "test_paths", "env_allowlist", "state_dir",
                                 "sandbox", "sealed"])
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
    for needed in ("scripts/factory/**", ".factory/**", "scripts/test.sh"):
        with pytest.raises(policy.PolicyError, match="protected"):
            policy.from_dict(_dump_variant(
                lambda d: d.update(protected_paths=[x for x in d["protected_paths"] if x != needed])))


def test_per_issue_cannot_exceed_per_day():
    with pytest.raises(policy.PolicyError, match="per_issue"):
        policy.from_dict(_dump_variant(lambda d: d["budget"].update(per_issue_usd=100.0, per_day_usd=10.0)))


def test_new_policy_fields_loaded():
    p = policy.load(REPO)
    assert "PATH" in p.env_allowlist and "HOME" in p.env_allowlist
    assert not any(any(w in n for w in ("TOKEN", "SECRET", "KEY")) for n in p.env_allowlist)
    assert p.state_dir.startswith("~") and p.test_paths


@pytest.mark.parametrize("bad", ["GH_TOKEN", "ANTHROPIC_API_KEY", "MY_SECRET", "A*", "", "lower case"])
def test_env_allowlist_rejects_secret_like_and_globs(bad):
    with pytest.raises(policy.PolicyError):
        policy.from_dict(_dump_variant(lambda d: d.update(env_allowlist=["PATH", bad])))


def test_state_dir_must_be_string():
    with pytest.raises(policy.PolicyError):
        policy.from_dict(_dump_variant(lambda d: d.update(state_dir=5)))


def test_shipped_sandbox_section():
    s = policy.load(REPO).sandbox
    assert s.mode == "actions"
    assert s.worker_workflow == "factory-worker.yml" and s.gates_workflow == "factory-gates.yml"
    assert s.poll_seconds >= 1 and s.timeout_minutes >= 1


def test_sandbox_local_mode_accepted():
    p = policy.from_dict(_dump_variant(lambda d: d["sandbox"].update(mode="local")))
    assert p.sandbox.mode == "local"


def test_sandbox_section_required():
    with pytest.raises(policy.PolicyError, match="sandbox"):
        policy.from_dict(_dump_variant(lambda d: d.pop("sandbox")))


@pytest.mark.parametrize("key,value", [
    ("mode", "docker"), ("mode", ""), ("mode", True),
    ("worker_workflow", "../evil.yml"), ("worker_workflow", "-x.yml"), ("worker_workflow", 5),
    ("worker_workflow", "a b.yml"), ("gates_workflow", "x"), ("gates_workflow", "a/b.yml"),
    ("verify_workflow", "x"), ("verify_workflow", "../v.yml"), ("verify_workflow", 3), ("verify_workflow", "a b.yml"),
    ("poll_seconds", 0), ("poll_seconds", "10"), ("poll_seconds", True), ("poll_seconds", 100000),
    ("timeout_minutes", 0), ("timeout_minutes", 1.5), ("timeout_minutes", 100000),
])
def test_sandbox_bad_values_rejected(key, value):
    with pytest.raises(policy.PolicyError, match="sandbox"):
        policy.from_dict(_dump_variant(lambda d: d["sandbox"].update({key: value})))


def test_sandbox_missing_and_unknown_keys_rejected():
    with pytest.raises(policy.PolicyError, match="sandbox"):
        policy.from_dict(_dump_variant(lambda d: d["sandbox"].pop("poll_seconds")))
    with pytest.raises(policy.PolicyError, match="sandbox"):
        policy.from_dict(_dump_variant(lambda d: d["sandbox"].update(extra=1)))


def test_shipped_sealed_and_verify_settings():
    p = policy.load(REPO)
    assert p.sealed.dir == "tests/sealed" and p.sealed.max_patch_bytes == 100000
    assert p.sandbox.verify_workflow == "factory-verify.yml"


@pytest.mark.parametrize("key,value", [
    ("dir", "tests/other"), ("dir", ""), ("dir", "/tests/sealed"), ("dir", "tests/sealed/"), ("dir", 5),
    ("dir", "tests/sealed/issue-1"), ("dir", "TESTS/SEALED"),
    ("max_patch_bytes", 0), ("max_patch_bytes", -1), ("max_patch_bytes", True), ("max_patch_bytes", "100"),
    ("max_patch_bytes", 1.5), ("max_patch_bytes", 10**9),
])
def test_sealed_bad_values_rejected(key, value):
    with pytest.raises(policy.PolicyError, match="sealed"):
        policy.from_dict(_dump_variant(lambda d: d["sealed"].update({key: value})))


def test_sealed_missing_and_unknown_keys_rejected():
    with pytest.raises(policy.PolicyError, match="sealed"):
        policy.from_dict(_dump_variant(lambda d: d["sealed"].pop("dir")))
    with pytest.raises(policy.PolicyError, match="sealed"):
        policy.from_dict(_dump_variant(lambda d: d["sealed"].pop("max_patch_bytes")))
    with pytest.raises(policy.PolicyError, match="sealed"):
        policy.from_dict(_dump_variant(lambda d: d["sealed"].update(extra=1)))


def test_sealed_must_be_a_map():
    with pytest.raises(policy.PolicyError, match="sealed"):
        policy.from_dict(_dump_variant(lambda d: d.update(sealed=["tests/sealed"])))

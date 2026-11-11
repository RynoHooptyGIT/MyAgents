"""Static checks on the sandbox workflows. PyYAML parses the key `on` as boolean True."""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[3]
WF = REPO / ".github" / "workflows"
FILES = ["factory-worker.yml", "factory-gates.yml", "factory-verify.yml"]
NO_SECRET_FILES = ["factory-gates.yml", "factory-verify.yml"]


def load(name):
    return yaml.safe_load((WF / name).read_text())


def steps(doc):
    out = []
    for job in doc["jobs"].values():
        out.extend(job["steps"])
    return out


def trigger(doc):
    return doc.get("on", doc.get(True))


@pytest.mark.parametrize("name", FILES)
def test_only_workflow_dispatch_trigger(name):
    t = trigger(load(name))
    assert set(t) == {"workflow_dispatch"} if isinstance(t, dict) else t == "workflow_dispatch"


@pytest.mark.parametrize("name", FILES)
def test_top_level_permissions_are_contents_read_only(name):
    assert load(name)["permissions"] == {"contents": "read"}
    for job in load(name)["jobs"].values():
        assert "permissions" not in job or job["permissions"] == {"contents": "read"}


@pytest.mark.parametrize("name", FILES)
def test_run_name_uses_request_id(name):
    prefix = name.replace(".yml", "")
    assert load(name)["run-name"] == prefix + " ${{ inputs.request_id }}"


@pytest.mark.parametrize("name", FILES)
def test_no_untrusted_expressions_in_run_bodies(name):
    for s in steps(load(name)):
        body = s.get("run", "")
        for bad in ("${{ inputs.", "${{inputs.", "${{ github.event", "${{github.event", "${{ secrets.", "${{secrets."):
            assert bad not in body, (s.get("name"), bad)


@pytest.mark.parametrize("name", FILES)
def test_no_expression_of_any_kind_in_run_bodies(name):
    for s in steps(load(name)):
        assert "${{" not in s.get("run", ""), s.get("name")


@pytest.mark.parametrize("name", FILES)
def test_every_checkout_does_not_persist_credentials_and_has_full_history(name):
    checkouts = [s for s in steps(load(name)) if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert len(checkouts) == 2
    for c in checkouts:
        assert c["with"]["persist-credentials"] is False
        assert c["with"]["fetch-depth"] == 0
    by_path = {c["with"]["path"]: c["with"] for c in checkouts}
    assert by_path["trusted"]["ref"] == "main"
    assert by_path["work"]["ref"] == "${{ inputs.branch }}"


@pytest.mark.parametrize("name", NO_SECRET_FILES)
def test_secret_free_workflows_have_no_secrets_at_all(name):
    assert "secrets" not in (WF / name).read_text().replace("secrets-free", "")


def test_worker_workflow_references_exactly_one_secret_in_one_step_env():
    text = (WF / "factory-worker.yml").read_text()
    assert set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text)) == {"FACTORY_CLAUDE_OAUTH_TOKEN"}
    assert text.count("secrets.") == 1
    holders = [s for s in steps(load("factory-worker.yml"))
               if "secrets." in yaml.dump(s.get("env", {})) or "secrets." in yaml.dump(s.get("with", {}))]
    assert len(holders) == 1
    h = holders[0]
    assert h["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "${{ secrets.FACTORY_CLAUDE_OAUTH_TOKEN }}"
    assert h["env"]["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] == "1"
    assert "with" not in h or "secrets." not in yaml.dump(h["with"])
    assert "sandbox_worker" in h["run"]
    assert "env" not in load("factory-worker.yml") and "env" not in next(iter(load("factory-worker.yml")["jobs"].values()))


def test_worker_workflow_shape():
    d = load("factory-worker.yml")
    job = next(iter(d["jobs"].values()))
    assert job["timeout-minutes"] == 60
    assert "concurrency" not in d and "concurrency" not in job
    inputs = trigger(d)["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"branch", "role", "model", "max_budget_usd", "request_id", "prompt_b64"}
    upload = [s for s in steps(d) if str(s.get("uses", "")).startswith("actions/upload-artifact@")][0]
    assert upload["if"] == "always()" and upload["with"]["name"] == "factory-result-${{ inputs.request_id }}"
    assert "changes.patch" in upload["with"]["path"] and "result.json" in upload["with"]["path"]


def test_gates_workflow_shape():
    d = load("factory-gates.yml")
    assert "concurrency" not in d and all("concurrency" not in j for j in d["jobs"].values())
    inputs = trigger(d)["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"branch", "request_id"}
    text = (WF / "factory-gates.yml").read_text()
    assert "bash trusted/scripts/factory/gates.sh work origin/main" in text
    upload = [s for s in steps(d) if str(s.get("uses", "")).startswith("actions/upload-artifact@")][0]
    assert upload["if"] == "always()" and upload["with"]["name"] == "factory-gates-${{ inputs.request_id }}"
    assert "gates-output.txt" in upload["with"]["path"]


@pytest.mark.parametrize("name", FILES)
def test_third_party_actions_are_pinned_to_full_sha(name):
    for s in steps(load(name)):
        if "uses" in s:
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", s["uses"]), s["uses"]


def test_policy_workflow_names_match_files():
    from .. import policy
    p = policy.load(REPO)
    assert (WF / p.sandbox.worker_workflow).is_file() and (WF / p.sandbox.gates_workflow).is_file()
    assert (WF / p.sandbox.verify_workflow).is_file()


def _dump(name):
    return yaml.dump(load(name))


@pytest.mark.parametrize("name", FILES)
def test_secrets_word_only_in_the_one_allowed_env_value(name):
    text = _dump(name)
    hits = re.findall(r"\bsecrets\b", text)
    if name in NO_SECRET_FILES:
        assert hits == []
    else:
        assert len(hits) == 1
        assert "${{ secrets.FACTORY_CLAUDE_OAUTH_TOKEN }}" in text
        assert text.count("secrets.FACTORY_CLAUDE_OAUTH_TOKEN") == 1
    for bad in ("toJSON(secrets", "toJson(secrets", "secrets[", "secrets ["):
        assert bad.lower() not in text.lower()


@pytest.mark.parametrize("name", FILES)
def test_no_github_token_anywhere(name):
    text = _dump(name) + (WF / name).read_text()
    for bad in ("github.token", "GH_TOKEN", "GITHUB_TOKEN"):
        assert bad.lower() not in text.lower().replace("persist-credentials", ""), bad
    for s in steps(load(name)):
        for k in (s.get("env") or {}):
            assert "TOKEN" not in k.upper() or k == "CLAUDE_CODE_OAUTH_TOKEN", k


def test_key_step_runs_from_trusted_and_no_key_step_runs_from_work():
    d = load("factory-worker.yml")
    key_steps = [s for s in steps(d) if "CLAUDE_CODE_OAUTH_TOKEN" in (s.get("env") or {})]
    assert len(key_steps) == 1
    assert key_steps[0]["working-directory"] == "trusted"
    for s in steps(d):
        wd = str(s.get("working-directory", ""))
        run = s.get("run", "")
        if wd.startswith("work") or re.search(r"(^|\s)(cd\s+)?work/", run) and "CLAUDE_CODE_OAUTH_TOKEN" in (s.get("env") or {}):
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in (s.get("env") or {})


@pytest.mark.parametrize("name", ["factory-worker.yml", "factory-verify.yml"])
def test_input_validation_precedes_checkout_of_the_branch(name):
    ss = steps(load(name))
    v = next(i for i, s in enumerate(ss) if "--validate-only" in s.get("run", ""))
    w = next(i for i, s in enumerate(ss) if str(s.get("uses", "")).startswith("actions/checkout@")
             and s["with"]["path"] == "work")
    t = next(i for i, s in enumerate(ss) if str(s.get("uses", "")).startswith("actions/checkout@")
             and s["with"]["path"] == "trusted")
    assert t < v < w


@pytest.mark.parametrize("name", FILES)
def test_runner_label_and_no_foreign_repository_checkout(name):
    for job in load(name)["jobs"].values():
        assert job["runs-on"] == "ubuntu-latest"
        assert "container" not in job
    for s in steps(load(name)):
        if str(s.get("uses", "")).startswith("actions/checkout@"):
            assert "repository" not in s["with"] and "token" not in s["with"]


@pytest.mark.parametrize("name", FILES)
def test_every_uses_is_pinned_by_40_hex_sha(name):
    uses = [s["uses"] for s in steps(load(name)) if "uses" in s]
    assert uses
    for u in uses:
        assert not u.startswith("./") and re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", u), u


def test_verify_workflow_shape():
    d = load("factory-verify.yml")
    job = next(iter(d["jobs"].values()))
    assert "concurrency" not in d and "concurrency" not in job
    assert job["timeout-minutes"] <= 60
    inputs = trigger(d)["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"branch", "request_id", "expected_sha", "issue", "sealed_b64"}
    assert inputs["sealed_b64"].get("required") is False and inputs["sealed_b64"].get("default") == ""
    for k in ("branch", "request_id", "expected_sha", "issue"):
        assert inputs[k]["required"] is True
    ss = steps(d)
    validate = [s for s in ss if "--validate-only" in s.get("run", "")]
    assert len(validate) == 1 and validate[0]["working-directory"] == "trusted"
    assert "sandbox_verify" in validate[0]["run"]
    run = [s for s in ss if s.get("run", "").strip().endswith("scripts.factory.sandbox_verify")]
    assert len(run) == 1 and run[0]["working-directory"] == "trusted"
    env = run[0]["env"]
    assert env["FACTORY_BRANCH"] == "${{ inputs.branch }}"
    assert env["FACTORY_REQUEST_ID"] == "${{ inputs.request_id }}"
    assert env["FACTORY_EXPECTED_SHA"] == "${{ inputs.expected_sha }}"
    assert env["FACTORY_ISSUE"] == "${{ inputs.issue }}"
    assert env["FACTORY_SEALED_B64"] == "${{ inputs.sealed_b64 }}"
    assert env["FACTORY_WORK_DIR"].endswith("/work") and env["FACTORY_OUT_DIR"].endswith("/out")
    upload = [s for s in ss if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert len(upload) == 1
    assert upload[0]["if"] == "always()" and upload[0]["with"]["name"] == "factory-verify-${{ inputs.request_id }}"
    assert "out/verify.json" in upload[0]["with"]["path"]


def test_verify_workflow_validate_step_has_the_same_env_as_the_run_step():
    ss = steps(load("factory-verify.yml"))
    v = next(s for s in ss if "--validate-only" in s.get("run", ""))
    r = next(s for s in ss if s.get("run", "").strip().endswith("scripts.factory.sandbox_verify"))
    for k in ("FACTORY_BRANCH", "FACTORY_REQUEST_ID", "FACTORY_EXPECTED_SHA", "FACTORY_ISSUE", "FACTORY_SEALED_B64"):
        assert v["env"][k] == r["env"][k]


def test_verify_workflow_uses_the_same_pinned_actions_as_gates():
    def pins(n):
        return {s["uses"] for s in steps(load(n)) if "uses" in s}
    assert pins("factory-verify.yml") <= pins("factory-worker.yml") | pins("factory-gates.yml")
    assert pins("factory-verify.yml")


def test_verify_workflow_is_dispatched_with_no_credentials_in_any_env():
    for s in steps(load("factory-verify.yml")):
        assert "ANTHROPIC" not in yaml.dump(s.get("env", {}))


@pytest.mark.parametrize("name", FILES)
def test_no_anthropic_api_key_anywhere_in_any_factory_workflow(name):
    # an API key in the environment would take precedence over the subscription token
    assert "ANTHROPIC_API_KEY" not in (WF / name).read_text()
    assert "FACTORY_ANTHROPIC_API_KEY" not in (WF / name).read_text()


def test_worker_workflow_maps_the_subscription_token_with_the_scrub_flag():
    holders = [s for s in steps(load("factory-worker.yml")) if "secrets." in yaml.dump(s.get("env", {}))]
    assert len(holders) == 1
    env = holders[0]["env"]
    assert env["CLAUDE_CODE_OAUTH_TOKEN"] == "${{ secrets.FACTORY_CLAUDE_OAUTH_TOKEN }}"
    assert env["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] == "1" and "ANTHROPIC_API_KEY" not in env

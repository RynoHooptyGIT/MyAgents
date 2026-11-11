"""Static checks on the sandbox workflows. PyYAML parses the key `on` as boolean True."""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[3]
WF = REPO / ".github" / "workflows"
FILES = ["factory-worker.yml", "factory-gates.yml"]


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


def test_gates_workflow_has_no_secrets_at_all():
    assert "secrets" not in (WF / "factory-gates.yml").read_text().replace("secrets-free", "")


def test_worker_workflow_references_exactly_one_secret_in_one_step_env():
    text = (WF / "factory-worker.yml").read_text()
    assert set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text)) == {"FACTORY_ANTHROPIC_API_KEY"}
    assert text.count("secrets.") == 1
    holders = [s for s in steps(load("factory-worker.yml"))
               if "secrets." in yaml.dump(s.get("env", {})) or "secrets." in yaml.dump(s.get("with", {}))]
    assert len(holders) == 1
    h = holders[0]
    assert h["env"]["ANTHROPIC_API_KEY"] == "${{ secrets.FACTORY_ANTHROPIC_API_KEY }}"
    assert h["env"]["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] == "1"
    assert "with" not in h or "secrets." not in yaml.dump(h["with"])
    assert "sandbox_worker" in h["run"]
    assert "env" not in load("factory-worker.yml") and "env" not in next(iter(load("factory-worker.yml")["jobs"].values()))


def test_worker_workflow_shape():
    d = load("factory-worker.yml")
    job = next(iter(d["jobs"].values()))
    assert job["timeout-minutes"] == 60
    assert d["concurrency"]["cancel-in-progress"] is False
    assert "inputs.branch" in d["concurrency"]["group"]
    inputs = trigger(d)["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"branch", "role", "model", "max_budget_usd", "request_id", "prompt_b64"}
    upload = [s for s in steps(d) if str(s.get("uses", "")).startswith("actions/upload-artifact@")][0]
    assert upload["if"] == "always()" and upload["with"]["name"] == "factory-result-${{ inputs.request_id }}"
    assert "changes.patch" in upload["with"]["path"] and "result.json" in upload["with"]["path"]


def test_gates_workflow_shape():
    d = load("factory-gates.yml")
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

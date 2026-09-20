import json, sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import instinct  # noqa: E402

TODAY = date(2026, 9, 19)

@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTINCTS_USER_DIR", str(tmp_path / "user"))
    (tmp_path / ".agents").mkdir()
    return tmp_path

def sample(**over):
    d = {"id": "prefer-gh-cli", "trigger": "when calling the GitHub API", "action": "use gh api",
         "confidence": 0.5, "domain": "workflow", "scope": "project", "status": "pending",
         "source": "session-observation", "project_name": "MyAgents",
         "evidence": ['2026-09-19 s1: user said "use gh"'], "observed_count": 3,
         "first_seen": "2026-09-19", "last_seen": "2026-09-19"}
    d.update(over); return d

def test_yaml_roundtrip_preserves_types_and_quotes():
    d = sample(trigger='when "quoting": things', evidence=["a: b", "123"])
    back = instinct.parse_instinct(instinct.dump_instinct(d))
    assert back == d
    assert isinstance(back["confidence"], float) and isinstance(back["observed_count"], int)
    assert back["evidence"][1] == "123"

def test_write_is_atomic_and_readable(root):
    p = instinct.project_dir(root) / "x.yaml"
    instinct.write_instinct(p, sample(id="x"))
    assert instinct.read_instinct(p)["id"] == "x"
    assert not list(p.parent.glob(".tmp-*"))

def test_read_rejects_malformed(root):
    p = instinct.project_dir(root); p.mkdir(parents=True)
    (p / "bad.yaml").write_text("id: bad\nstatus: bogus\n")
    (p / "nope.yaml").write_text("just text")
    items, bad = instinct.load_tier(p, "project")
    assert items == [] and len(bad) == 2

@pytest.mark.parametrize("n,expected", [(1, 0.3), (2, 0.3), (3, 0.5), (5, 0.5), (6, 0.7), (10, 0.7), (11, 0.85)])
def test_initial_confidence(n, expected):
    assert instinct.initial_confidence(n) == expected

def test_effective_confidence_decays_with_floor():
    d = sample(confidence=0.7, last_seen="2026-08-22")  # 4 weeks
    assert instinct.effective_confidence(d, TODAY, 0.02) == pytest.approx(0.62)
    d = sample(confidence=0.32, last_seen="2026-01-01")
    assert instinct.effective_confidence(d, TODAY, 0.02) == 0.3

def test_validate_normalizes_and_rejects():
    ok = instinct.validate({"id": "use-gh", "trigger": "t", "action": "a", "domain": "nope", "observed_count": 4})
    assert ok["domain"] == "workflow" and ok["scope"] == "project" and ok["confidence"] == 0.5
    assert instinct.validate({"id": "Bad Id", "trigger": "t", "action": "a"}) is None
    assert instinct.validate({"id": "ok-id", "trigger": "", "action": "a"}) is None
    assert instinct.validate("nope") is None

def test_extract_json_array_tolerates_fences():
    text = "Here you go:\n```json\n[{\"id\": \"a-b-c\"}]\n```\n"
    assert instinct.extract_json_array(text) == [{"id": "a-b-c"}]
    assert instinct.extract_json_array("no json") == []

def test_ingest_creates_pending_then_merges(root):
    r = instinct.ingest(root, [{"id": "use-gh-api", "trigger": "t", "action": "a", "evidence": ["e1"]}], TODAY, "MyAgents")
    assert r["created"] == ["use-gh-api"]
    d = instinct.read_instinct(instinct.project_dir(root) / "use-gh-api.yaml")
    assert d["status"] == "pending" and d["confidence"] == 0.3 and d["project_name"] == "MyAgents"
    r = instinct.ingest(root, [{"id": "use-gh-api", "trigger": "t", "action": "a", "evidence": ["e2"], "observed_count": 2}], TODAY, "MyAgents")
    assert r["merged"] == ["use-gh-api"]
    d = instinct.read_instinct(instinct.project_dir(root) / "use-gh-api.yaml")
    assert d["observed_count"] == 3 and d["confidence"] == 0.5 and d["evidence"] == ["e1", "e2"]

def test_ingest_never_resurrects_rejected(root):
    instinct.write_instinct(instinct.project_dir(root) / "dead.yaml", sample(id="dead", status="rejected"))
    r = instinct.ingest(root, [{"id": "dead", "trigger": "t", "action": "a"}], TODAY, "P")
    assert r["dropped"] == 1 and instinct.read_instinct(instinct.project_dir(root) / "dead.yaml")["status"] == "rejected"

def test_ingest_contradiction_lowers_confidence(root):
    instinct.write_instinct(instinct.project_dir(root) / "old.yaml", sample(id="old", confidence=0.7, status="active"))
    r = instinct.ingest(root, [{"id": "old", "trigger": "t", "action": "a", "contradicts": "old"}], TODAY, "P")
    assert r["contradicted"] == ["old"] and r["merged"] == []
    assert instinct.read_instinct(instinct.project_dir(root) / "old.yaml")["confidence"] == 0.6

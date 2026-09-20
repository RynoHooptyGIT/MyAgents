import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import instinct, prefilter  # noqa: E402

def ev(event, **k):
    d = {"ts": "t", "session_id": "s", "event": event}; d.update(k); return d

def tool(name, inp, err=False, resp=""):
    return ev("tool", tool=name, input=json.dumps(inp), response=resp, is_error=err)

def write(root, events):
    p = instinct.learnings_dir(root) / "observations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(e) + "\n" for e in events))
    return p

def test_correction_bundles_preceding_tools():
    events = [tool("Bash", {"command": "curl x"}), tool("Edit", {"file_path": "a.py"}), ev("prompt", text="No, use gh instead")]
    c = prefilter.find_candidates(events)
    assert [x["kind"] for x in c] == ["correction"]
    assert len(c[0]["window"]) == 3 and c[0]["window"][-1]["event"] == "prompt"

def test_correction_ignores_late_matches():
    assert prefilter.find_candidates([ev("prompt", text="x" * 130 + " actually")]) == []

def test_error_resolution_same_tool_within_three():
    events = [tool("Bash", {"command": "pytest"}, err=True), tool("Read", {"file_path": "t.py"}), tool("Bash", {"command": "pytest"})]
    c = prefilter.find_candidates(events)
    assert c[0]["kind"] == "error_resolution" and len(c[0]["window"]) == 3
    events = [tool("Bash", {"command": "x"}, err=True)] + [tool("Read", {"file_path": "t"})] * 3 + [tool("Bash", {"command": "x"})]
    assert prefilter.find_candidates(events) == []

def test_repetition_signature_threshold():
    events = [tool("Bash", {"command": "gh pr view 1"}), tool("Bash", {"command": "gh api x"}), tool("Bash", {"command": "gh issue list"}),
              tool("Edit", {"file_path": "a.ts"}), tool("Edit", {"file_path": "b.ts"})]
    c = prefilter.find_candidates(events)
    assert len(c) == 1 and c[0]["kind"] == "repetition" and c[0]["signature"] == "Bash:gh" and c[0]["count"] == 3

def test_window_strings_truncated():
    c = prefilter.find_candidates([tool("Bash", {"command": "x" * 3000}, err=True), tool("Bash", {"command": "y"})])
    assert len(c[0]["window"][0]["input"]) == 1000

def test_read_new_honors_offset_and_rotation(tmp_path):
    p = tmp_path / "o.jsonl"
    p.write_text('{"a":1}\n{"a":2}\n')
    events, off = prefilter.read_new(p, 0)
    assert [e["a"] for e in events] == [1, 2] and off == p.stat().st_size
    assert prefilter.read_new(p, off) == ([], off)
    p.write_text('{"a":3}\n')  # rotated: file now smaller than offset
    events, off2 = prefilter.read_new(p, off)
    assert [e["a"] for e in events] == [3] and off2 == p.stat().st_size

def test_main_commit_writes_watermark_and_rejected_ids(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INSTINCTS_USER_DIR", str(tmp_path / "u"))
    (tmp_path / ".agents").mkdir()
    write(tmp_path, [ev("prompt", text="nope, not that"), tool("Bash", {"command": "x"})])
    instinct.write_instinct(instinct.project_dir(tmp_path) / "dead.yaml",
                            {"id": "dead", "trigger": "t", "action": "a", "confidence": 0.3, "status": "rejected", "evidence": []})
    assert prefilter.main(["--root", str(tmp_path), "--commit"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["count"] == 1 and out["rejected_ids"] == ["dead"]
    assert int((instinct.learnings_dir(tmp_path) / ".instinct-watermark").read_text()) == out["new_offset"]
    assert prefilter.main(["--root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 0

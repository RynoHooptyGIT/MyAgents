import io, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import observe  # noqa: E402

def test_scrub_key_value_forms():
    assert observe.scrub("API_KEY=abc123 and token: xyz") == "API_KEY=[REDACTED] and token: [REDACTED]"
    assert observe.scrub('{"api_key": "abc", "x": 1}') == '{"api_key": "[REDACTED]", "x": 1}'
    assert observe.scrub("nothing here") == "nothing here"

def test_detect_error_from_fields_and_text():
    assert observe.detect_error({"exit_code": 1}, "") is True
    assert observe.detect_error({"is_error": True}, "") is True
    assert observe.detect_error(None, "Traceback (most recent call last):\n...") is True
    assert observe.detect_error({"exit_code": 0}, "all good") is False

def test_build_record_truncates_and_scrubs():
    rec = observe.build_record("tool", {"session_id": "s1", "tool_name": "Bash",
                                        "tool_input": {"command": "x" * 6000},
                                        "tool_response": {"stdout": "SECRET=hunter2", "exit_code": 0}}, "2026-09-19T00:00:00Z")
    assert rec["event"] == "tool" and rec["tool"] == "Bash" and len(rec["input"]) == 5000
    assert "[REDACTED]" in rec["response"] and rec["is_error"] is False
    rec = observe.build_record("prompt", {"session_id": "s1", "prompt": "p" * 3000}, "t")
    assert rec["event"] == "prompt" and len(rec["text"]) == 2000

def test_append_and_rotate(tmp_path):
    p = tmp_path / "observations.jsonl"
    observe.append_record(p, {"a": 1}, max_mb=10)
    observe.append_record(p, {"a": 2}, max_mb=10)
    assert [json.loads(l)["a"] for l in p.read_text().splitlines()] == [1, 2]
    p.write_text("x" * (1024 * 1024 + 1))
    observe.append_record(p, {"a": 3}, max_mb=1)
    assert (tmp_path / "observations.jsonl.1").exists() and json.loads(p.read_text())["a"] == 3

def test_main_writes_under_root_and_is_silent(tmp_path, capsys):
    (tmp_path / ".agents").mkdir()
    rc = observe.main(["prompt", "--root", str(tmp_path)], stdin=io.StringIO('{"session_id":"s","prompt":"hi"}'))
    assert rc == 0 and capsys.readouterr().out == ""
    line = json.loads((tmp_path / "team/_memory/_learnings/observations.jsonl").read_text())
    assert line["text"] == "hi" and line["event"] == "prompt"

def test_main_respects_off_marker_and_disabled(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".instincts-off").touch()
    observe.main(["prompt", "--root", str(tmp_path)], stdin=io.StringIO('{"prompt":"hi"}'))
    assert not (tmp_path / "team/_memory/_learnings/observations.jsonl").exists()
    (tmp_path / ".instincts-off").unlink()
    (tmp_path / ".agents/config.yaml").write_text("instincts:\n  enabled: false\n")
    observe.main(["prompt", "--root", str(tmp_path)], stdin=io.StringIO('{"prompt":"hi"}'))
    assert not (tmp_path / "team/_memory/_learnings/observations.jsonl").exists()

def test_main_bad_json_is_noop(tmp_path):
    (tmp_path / ".agents").mkdir()
    assert observe.main(["tool", "--root", str(tmp_path)], stdin=io.StringIO("not json")) == 0

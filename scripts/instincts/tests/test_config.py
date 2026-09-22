import subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

BLOCK = """coordination:
  heartbeat_interval_calls: 20

instincts:
  enabled: false           # off for this test
  model: sonnet
  min_candidates: 5
  min_confidence: 0.6
  # a comment line
other:
  x: 1
"""

def test_defaults_when_no_file(tmp_path):
    cfg = config.load(tmp_path)
    assert cfg == config.DEFAULTS

def test_parses_block_and_ignores_other_sections(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "config.yaml").write_text(BLOCK)
    cfg = config.load(tmp_path)
    assert cfg["enabled"] is False
    assert cfg["model"] == "sonnet"
    assert cfg["min_candidates"] == 5
    assert cfg["min_confidence"] == 0.6
    assert cfg["inject_limit"] == config.DEFAULTS["inject_limit"]

def test_bad_values_fall_back(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "config.yaml").write_text("instincts:\n  min_candidates: many\n  enabled: yes\n")
    cfg = config.load(tmp_path)
    assert cfg["min_candidates"] == config.DEFAULTS["min_candidates"]
    assert cfg["enabled"] is True

    # Test unparsable bool falls back to default
    (tmp_path / ".agents" / "config.yaml").write_text("instincts:\n  enabled: banana\n")
    cfg = config.load(tmp_path)
    assert cfg["enabled"] is True  # falls back to default

    # Test recognized false word
    (tmp_path / ".agents" / "config.yaml").write_text("instincts:\n  enabled: off\n")
    cfg = config.load(tmp_path)
    assert cfg["enabled"] is False

def test_cli_prints_requested_keys(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "config.yaml").write_text("instincts:\n  model: haiku\n  min_candidates: 4\n")
    out = subprocess.run(
        [sys.executable, str(Path(config.__file__)), "--root", str(tmp_path), "enabled", "model", "min_candidates"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    assert out == ["True", "haiku", "4"]

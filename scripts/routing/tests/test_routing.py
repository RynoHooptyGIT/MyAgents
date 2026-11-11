import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import apply_model  # noqa: E402
import estimate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CFG = json.loads((ROOT / "templates/model-routing.json").read_text())


def test_choose_cheapest_adequate_tier():
    assert estimate.choose(CFG, "light") == "haiku"
    assert estimate.choose(CFG, "standard") == "sonnet"
    assert estimate.choose(CFG, "high") == "opus"
    assert estimate.choose(CFG, "frontier") == "fable"


def test_cost_and_verdict():
    m = CFG["models"]["sonnet"]
    assert estimate.cost(m, 1_000_000, 1_000_000) == 18.0
    b = CFG["budget"]
    assert estimate.verdict(0.5, b) == "ok"
    assert estimate.verdict(1.0, b) == "confirm"
    assert estimate.verdict(10.0, b) == "block"


def test_cli_blocks_over_budget():
    script = ROOT / "scripts/routing/estimate.py"
    base = [sys.executable, str(script), "--config", str(ROOT / "templates/model-routing.json")]
    ok = subprocess.run(base + ["--in", "1000", "--out", "1000", "--tier", "light"], capture_output=True, text=True)
    assert ok.returncode == 0 and "model=haiku" in ok.stdout
    big = subprocess.run(base + ["--in", "5000000", "--out", "1000000", "--model", "fable"], capture_output=True, text=True)
    assert big.returncode == 3 and "verdict=block" in big.stdout


def test_unknown_tier_is_an_error():
    assert estimate.main(["--in", "1", "--out", "1", "--tier", "nope"]) == 1


def test_apply_model_preserves_other_settings(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude/settings.json").write_text('{"permissions": {"allow": ["Read"]}, "model": "sonnet"}')
    assert apply_model.apply(tmp_path) is True
    data = json.loads((tmp_path / ".claude/settings.json").read_text())
    assert data["model"] == "fable" and data["permissions"] == {"allow": ["Read"]}
    assert apply_model.apply(tmp_path) is False


def test_apply_model_creates_file(tmp_path):
    assert apply_model.apply(tmp_path) is True
    assert json.loads((tmp_path / ".claude/settings.json").read_text()) == {"model": "fable"}

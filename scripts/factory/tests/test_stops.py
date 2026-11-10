from datetime import datetime, timezone
from pathlib import Path

from .. import policy as pol
from .. import stops as S
from .. import tracker as T

POLICY = pol.load(Path(__file__).resolve().parents[3])
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)


def rows_costing(total):
    return [dict(ts=NOW.isoformat(), cost_usd=total)]


def tr(labels_by_issue=()):
    f = T.FakeTracker(["owner"])
    for n, labels in labels_by_issue:
        f.add_issue(n, "t", "", "owner", labels, "2026-01-01")
    return f


def test_clear_when_nothing_trips(tmp_path):
    assert S.new_claim_block(tmp_path, tr(), [], POLICY, NOW) is None


def test_stop_file_blocks(tmp_path):
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "STOP").write_text("")
    r = S.new_claim_block(tmp_path, tr(), [], POLICY, NOW)
    assert r and "STOP" in r


def test_stop_file_directory_or_symlink_still_blocks(tmp_path):
    (tmp_path / ".factory" / "STOP").mkdir(parents=True)
    assert S.new_claim_block(tmp_path, tr(), [], POLICY, NOW)


def test_halt_label_blocks(tmp_path):
    r = S.new_claim_block(tmp_path, tr([(1, ["factory:halt"])]), [], POLICY, NOW)
    assert r and "halt" in r


def test_day_budget_blocks_at_cap(tmp_path):
    assert S.new_claim_block(tmp_path, tr(), rows_costing(POLICY.per_day_usd - 0.01), POLICY, NOW) is None
    r = S.new_claim_block(tmp_path, tr(), rows_costing(POLICY.per_day_usd), POLICY, NOW)
    assert r and "daily" in r


def test_yesterdays_spend_does_not_block(tmp_path):
    old = [dict(ts=datetime(2026, 11, 9, 23, 0, tzinfo=timezone.utc).isoformat(), cost_usd=999)]
    assert S.new_claim_block(tmp_path, tr(), old, POLICY, NOW) is None


def test_awaiting_human_cap_blocks(tmp_path):
    n = POLICY.max_awaiting_human
    t = tr([(i, ["factory:awaiting-human"]) for i in range(1, n)])
    assert S.new_claim_block(tmp_path, t, [], POLICY, NOW) is None
    t = tr([(i, ["factory:awaiting-human"]) for i in range(1, n + 1)])
    r = S.new_claim_block(tmp_path, t, [], POLICY, NOW)
    assert r and "awaiting-human" in r


def test_issue_budget_refuses_at_cap():
    assert S.issue_budget_block(POLICY.per_issue_usd - 0.01, POLICY) is None
    assert "per-issue" in S.issue_budget_block(POLICY.per_issue_usd, POLICY)


def test_run_day_budget_includes_spend_this_run():
    # 24 already spent today + 1.5 this run crosses a 25 cap
    assert S.day_budget_block(24.0, 1.5, POLICY) is not None
    assert S.day_budget_block(24.0, 0.5, POLICY) is None

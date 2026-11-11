import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from .. import ledger as L
from .. import policy as pol

POLICY = pol.load(Path(__file__).resolve().parents[3])
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
LATE = T0 + timedelta(days=200)


def row(issue=1, outcome="merged", category="skills", ts=T0, tier="T1", protected=False, cost=0.5, **kw):
    r = dict(ts=ts.isoformat(), issue=issue, tier=tier, reasons=[], category=category,
             protected=protected, models={"build": ["sonnet"]}, tokens={"input": 10, "output": 5},
             cost_usd=cost, retries=0, outcome=outcome, started_at=ts.isoformat(),
             finished_at=ts.isoformat())
    r.update(kw)
    return r


def test_append_and_read_roundtrip(tmp_path):
    led = L.Ledger(tmp_path / ".factory" / "ledger.jsonl")
    led.append(row(1))
    led.append(row(2))
    rows = led.rows()
    assert [r["issue"] for r in rows] == [1, 2]
    lines = (tmp_path / ".factory" / "ledger.jsonl").read_text().splitlines()
    assert len(lines) == 2 and all(json.loads(l) for l in lines)


def test_append_only_never_rewrites(tmp_path):
    p = tmp_path / "l.jsonl"
    led = L.Ledger(p)
    led.append(row(1))
    before = p.read_bytes()
    led.append(row(2))
    assert p.read_bytes().startswith(before)


def test_missing_file_reads_empty(tmp_path):
    assert L.Ledger(tmp_path / "nope.jsonl").rows() == []


@pytest.mark.parametrize("mutate", [
    lambda r: r.pop("issue"), lambda r: r.pop("tier"), lambda r: r.update(tier="T9"),
    lambda r: r.update(outcome="weird"), lambda r: r.update(cost_usd=-1),
    lambda r: r.update(issue="1"), lambda r: r.update(retries=-1), lambda r: r.update(ts="yesterday"),
    lambda r: r.update(reasons="x"), lambda r: r.update(tokens={"input": 1}),
])
def test_invalid_row_rejected_and_not_written(tmp_path, mutate):
    led = L.Ledger(tmp_path / "l.jsonl")
    r = row(1)
    mutate(r)
    with pytest.raises(L.LedgerError):
        led.append(r)
    assert not (tmp_path / "l.jsonl").exists()


def test_corrupt_line_is_error_not_skipped(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text(json.dumps(row(1)) + "\n{not json\n")
    with pytest.raises(L.LedgerError, match="line 2"):
        L.Ledger(p).rows()


def test_spent_on_day(tmp_path):
    rows = [row(1, cost=1.0), row(2, cost=2.5), row(3, cost=9.0, ts=T0 - timedelta(days=1))]
    assert L.spent_on(rows, T0.date()) == 3.5


def test_summary_counts():
    rows = [row(1, outcome="merged"), row(2, outcome="awaiting-human", tier="T2"),
            row(3, outcome="failed", tier="T2")]
    s = L.summarize(rows)
    assert s["total"] == 3 and s["by_outcome"]["merged"] == 1
    assert s["by_tier"]["T2"] == 2 and s["cost_usd"] == 1.5


# ---- earned level ----
def merged_series(n, category="skills", start=T0, protected=False):
    return [row(i, "merged", category, start + timedelta(hours=i), protected=protected) for i in range(1, n + 1)]


def test_starts_at_t2():
    assert L.earned_level([], "skills", POLICY, now=LATE) == "T2"


def test_four_merges_still_t2_five_promotes():
    assert L.earned_level(merged_series(4), "skills", POLICY, now=LATE) == "T2"
    assert L.earned_level(merged_series(5), "skills", POLICY, now=LATE) == "T1"


def test_other_categories_do_not_count():
    assert L.earned_level(merged_series(9, "docs"), "skills", POLICY, now=LATE) == "T2"


def test_non_merged_rows_do_not_count():
    rows = merged_series(4) + [row(50, "awaiting-human", ts=T0 + timedelta(days=1))]
    assert L.earned_level(rows, "skills", POLICY, now=LATE) == "T2"


def test_revert_demotes_and_resets_count():
    rows = merged_series(5)
    rows.append(row(2, "reverted", ts=T0 + timedelta(days=1)))
    assert L.earned_level(rows, "skills", POLICY, now=LATE) == "T2"
    # after a revert, five more clean merges are required
    more = merged_series(4, start=T0 + timedelta(days=2))
    for i, m in enumerate(more):
        m["issue"] = 100 + i
    assert L.earned_level(rows + more, "skills", POLICY, now=LATE) == "T2"
    last = row(200, "merged", ts=T0 + timedelta(days=3))
    assert L.earned_level(rows + more + [last], "skills", POLICY, now=LATE) == "T1"


def test_revert_of_t2_category_stays_t2_and_resets_count():
    rows = merged_series(3) + [row(1, "reverted", ts=T0 + timedelta(days=1))]
    rows += [row(10 + i, "merged", ts=T0 + timedelta(days=2, hours=i)) for i in range(4)]
    assert L.earned_level(rows, "skills", POLICY, now=LATE) == "T2"


def test_protected_rows_never_promote():
    assert L.earned_level(merged_series(9, protected=True), "skills", POLICY, now=LATE) == "T2"


def test_rows_processed_in_timestamp_order_not_file_order():
    rows = merged_series(5)
    rev = row(2, "reverted", ts=T0 + timedelta(days=1))
    # revert listed first in the file but happened last
    assert L.earned_level([rev] + rows, "skills", POLICY, now=LATE) == "T2"


def test_revert_of_other_category_ignored():
    rows = merged_series(5) + [row(2, "reverted", "docs", ts=T0 + timedelta(days=1))]
    assert L.earned_level(rows, "skills", POLICY, now=LATE) == "T1"


def test_promotion_count_comes_from_policy():
    p3 = POLICY.__class__(**{**POLICY.__dict__, "promotion_count": 3})
    assert L.earned_level(merged_series(3), "skills", p3, now=LATE) == "T1"


# ---- revert window and T0 exclusion ----
NOW = T0 + timedelta(days=100)


def test_merge_counts_only_after_revert_window():
    p = POLICY
    recent = [row(i, "merged", ts=NOW - timedelta(days=1, hours=-i)) for i in range(1, 6)]
    assert L.earned_level(recent, "skills", p, now=NOW) == "T2"
    old = [row(i, "merged", ts=NOW - timedelta(days=p.revert_window_days + 1, hours=-i)) for i in range(1, 6)]
    assert L.earned_level(old, "skills", p, now=NOW) == "T1"


def test_window_boundary_exact():
    p = POLICY
    rows = [row(i, "merged", ts=NOW - timedelta(days=p.revert_window_days, seconds=-i)) for i in range(1, 6)]
    assert L.earned_level(rows, "skills", p, now=NOW) == "T2"       # one second short
    rows = [row(i, "merged", ts=NOW - timedelta(days=p.revert_window_days, seconds=i)) for i in range(1, 6)]
    assert L.earned_level(rows, "skills", p, now=NOW) == "T1"


def test_revert_inside_window_cancels_the_pending_merge():
    p = POLICY
    base = NOW - timedelta(days=40)
    rows = [row(i, "merged", ts=base + timedelta(hours=i)) for i in range(1, 6)]
    rows.append(row(3, "reverted", ts=base + timedelta(days=2)))
    assert L.earned_level(rows, "skills", p, now=NOW) == "T2"


def test_t0_merges_do_not_promote_a_code_category():
    rows = [row(i, "merged", ts=T0 + timedelta(hours=i), tier="T0") for i in range(1, 10)]
    assert L.earned_level(rows, "skills", POLICY, now=NOW) == "T2"


def test_cost_known_and_notes_optional_fields(tmp_path):
    led = L.Ledger(tmp_path / "l.jsonl")
    led.append(row(1, cost_known=False, notes=["forced removal"]))
    assert led.rows()[0]["cost_known"] is False
    with pytest.raises(L.LedgerError):
        led.append(row(2, cost_known="no"))
    with pytest.raises(L.LedgerError):
        led.append(row(3, notes="x"))


def test_sandbox_field_optional_and_validated(tmp_path):
    led = L.Ledger(tmp_path / "l.jsonl")
    led.append(row(1))                      # old rows have no sandbox field and still load
    led.append(row(2, sandbox="actions"))
    led.append(row(3, sandbox="local"))
    assert [r.get("sandbox") for r in led.rows()] == [None, "actions", "local"]
    for bad in ("docker", "", 5, None):
        with pytest.raises(L.LedgerError):
            led.append(row(4, sandbox=bad))


def test_old_row_on_disk_without_sandbox_loads(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text(json.dumps(row(1)) + "\n")
    assert L.Ledger(p).rows()[0]["issue"] == 1


VERIFY = {"model_verdict": "agree", "revert_check": "fails_without_change", "sealed_available": True,
          "sealed_total": 3, "sealed_failed": 0}


def _row(**over):  # noqa
    r = {"ts": "2026-11-10T09:00:00+00:00", "issue": 1, "tier": "T2", "reasons": [], "category": "x",
         "protected": False, "models": {}, "tokens": {"input": 0, "output": 0}, "cost_usd": 0.0,
         "retries": 0, "outcome": "awaiting-human", "started_at": "2026-11-10T09:00:00+00:00",
         "finished_at": "2026-11-10T09:01:00+00:00"}
    r.update(over)
    return r


def test_verify_object_is_optional_and_round_trips(tmp_path):
    led = L.Ledger(tmp_path / "l.jsonl")
    led.append(_row())
    led.append(_row(verify=VERIFY))
    rows = led.rows()
    assert "verify" not in rows[0] and rows[1]["verify"] == VERIFY


@pytest.mark.parametrize("mutate", [
    lambda v: v.update(model_verdict="great"), lambda v: v.update(model_verdict=None),
    lambda v: v.update(revert_check=3), lambda v: v.update(sealed_available="yes"),
    lambda v: v.update(sealed_total=-1), lambda v: v.update(sealed_failed=True),
    lambda v: v.pop("sealed_total"), lambda v: v.update(extra=1),
])
def test_bad_verify_object_rejected(tmp_path, mutate):
    v = dict(VERIFY)
    mutate(v)
    led = L.Ledger(tmp_path / "l.jsonl")
    with pytest.raises(L.LedgerError):
        led.append(_row(verify=v))
    assert not (tmp_path / "l.jsonl").exists()


def test_verify_must_be_an_object(tmp_path):
    with pytest.raises(L.LedgerError):
        L.Ledger(tmp_path / "l.jsonl").append(_row(verify="agree"))


def test_old_row_without_verify_loads(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text(json.dumps(_row()) + "\n")
    assert L.Ledger(p).rows()[0]["outcome"] == "awaiting-human"

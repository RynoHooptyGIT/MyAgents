from pathlib import Path

import pytest

from .. import policy as pol
from .. import retry as R

POLICY = pol.load(Path(__file__).resolve().parents[3])
OUT = "collected 3 items\nFAILED tests/test_a.py::test_x - assert 1 == 2\nE   assert 1 == 2\nnoise line\nTESTS: pytest 2 passed\n"


def test_round_one_same_model_full_output():
    ladder = R.Ladder(POLICY)
    first = R.attempt_record(0, "sonnet", "spec text")
    plan = ladder.next_attempt([first], OUT)
    assert plan.round == 1 and plan.model == "sonnet"
    assert plan.context == OUT


def test_round_two_different_model_only_failing_text():
    ladder = R.Ladder(POLICY)
    h = [R.attempt_record(0, "sonnet", "spec"), R.attempt_record(1, "sonnet", OUT)]
    plan = ladder.next_attempt(h, OUT)
    assert plan.round == 2 and plan.model == "fable" and plan.model != "sonnet"
    assert "assert 1 == 2" in plan.context
    assert "noise line" not in plan.context and "collected 3 items" not in plan.context


def test_after_round_two_is_exhausted():
    ladder = R.Ladder(POLICY)
    h = [R.attempt_record(0, "sonnet", "s"), R.attempt_record(1, "sonnet", "a"),
         R.attempt_record(2, "fable", "b")]
    assert ladder.next_attempt(h, OUT) is None


def test_empty_history_rejected():
    with pytest.raises(ValueError):
        R.Ladder(POLICY).next_attempt([], OUT)


def test_identical_retry_refused():
    prev = R.attempt_record(1, "sonnet", OUT)
    with pytest.raises(R.IdenticalRetry):
        R.check_not_identical([R.attempt_record(0, "sonnet", "s"), prev], "sonnet", OUT)


def test_different_model_or_input_allowed():
    prev = [R.attempt_record(1, "sonnet", OUT)]
    R.check_not_identical(prev, "fable", OUT)
    R.check_not_identical(prev, "sonnet", OUT + "x")


def test_ladder_refuses_when_round_two_would_repeat_builder_model_and_input(monkeypatch):
    # Defensive: even if routing were misconfigured, an identical retry is refused.
    bad = POLICY.__class__(**{**POLICY.__dict__, "routing": {**POLICY.routing, "retry_round_2": "sonnet"}})
    ladder = R.Ladder(bad)
    h = [R.attempt_record(0, "sonnet", "s"), R.attempt_record(1, "sonnet", R.extract_failures(OUT))]
    with pytest.raises(R.IdenticalRetry):
        ladder.next_attempt(h, OUT)


def test_extract_failures_fallback_to_tail():
    text = "\n".join(f"line {i}" for i in range(100))
    out = R.extract_failures(text)
    assert "line 99" in out and "line 0\n" not in out


def test_extract_failures_caps_length():
    text = "\n".join("FAILED x" * 50 for _ in range(500))
    assert len(R.extract_failures(text)) <= R.MAX_FAILURE_CHARS


def test_extract_failures_none():
    assert R.extract_failures("") == ""

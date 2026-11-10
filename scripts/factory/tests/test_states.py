import pytest

from .. import states as s


LEGAL = [
    ("proposed", "queued"), ("queued", "claimed"), ("claimed", "building"),
    ("building", "verifying"), ("verifying", "merge-ready"), ("merge-ready", "done"),
    ("claimed", "awaiting-human"), ("building", "awaiting-human"),
    ("verifying", "awaiting-human"), ("merge-ready", "awaiting-human"),
    ("claimed", "failed"), ("building", "failed"), ("verifying", "failed"),
    ("awaiting-human", "queued"), ("awaiting-human", "done"), ("failed", "queued"),
]


@pytest.mark.parametrize("a,b", LEGAL)
def test_legal(a, b):
    s.check_transition(a, b)


def test_every_other_pair_is_illegal():
    for a in s.STATES:
        for b in s.STATES:
            if (a, b) not in LEGAL:
                with pytest.raises(s.IllegalTransition):
                    s.check_transition(a, b)


def test_no_skipping_and_done_is_terminal():
    for bad in [("queued", "building"), ("queued", "done"), ("building", "merge-ready"),
                ("done", "queued"), ("queued", "queued")]:
        with pytest.raises(s.IllegalTransition):
            s.check_transition(*bad)


def test_unknown_state_raises():
    with pytest.raises(s.IllegalTransition):
        s.check_transition("queued", "bogus")


def test_label_roundtrip():
    assert s.label("queued") == "factory:queued"
    assert s.state_from_label("factory:merge-ready") == "merge-ready"
    assert s.state_from_label("bug") is None
    assert s.state_from_label("factory:halt") is None


def test_state_of_labels_requires_exactly_one():
    assert s.state_of(["bug", "factory:queued"]) == "queued"
    with pytest.raises(s.IllegalTransition):
        s.state_of(["factory:queued", "factory:building"])
    with pytest.raises(s.IllegalTransition):
        s.state_of(["bug"])

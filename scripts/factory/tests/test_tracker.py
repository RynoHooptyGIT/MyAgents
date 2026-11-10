import json

import pytest

from .. import states
from .. import tracker as t
from ..proc import ProcResult

EVIL = 'x"; rm -rf ~ #$(touch /tmp/pwned)`id`\n--repo evil/evil'


class FakeRunner:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [])

    def __call__(self, argv, cwd=None, input_text=None, timeout=None):
        self.calls.append(list(argv))
        if self.responses:
            r = self.responses.pop(0)
            return r if isinstance(r, ProcResult) else ProcResult(0, r, "")
        return ProcResult(0, "[]", "")


def gh_issue(n, author="owner", labels=("factory:queued",), created="2026-01-0%dT00:00:00Z", title="t", body="b"):
    return {"number": n, "title": title, "body": body, "author": {"login": author},
            "labels": [{"name": x} for x in labels],
            "createdAt": created % n if "%d" in created else created}


# ---------- fake ----------
def test_fake_lists_oldest_first_and_only_queued():
    f = t.FakeTracker(allowed_authors=["owner"])
    f.add_issue(2, "b", "", "owner", ["factory:queued"], "2026-01-02")
    f.add_issue(1, "a", "", "owner", ["factory:queued"], "2026-01-01")
    f.add_issue(3, "c", "", "owner", ["factory:building"], "2026-01-00")
    assert [i.number for i in f.list_queued()] == [1, 2]


def test_fake_transition_validates():
    f = t.FakeTracker(allowed_authors=["owner"])
    f.add_issue(1, "a", "", "owner", ["factory:queued"], "2026-01-01")
    f.transition(1, "queued", "claimed")
    assert f.labels(1) == {"factory:claimed"}
    with pytest.raises(states.IllegalTransition):
        f.transition(1, "claimed", "done")
    with pytest.raises(t.StateMismatch):
        f.transition(1, "queued", "claimed")   # not queued any more


def test_fake_refuses_to_claim_non_allowlisted():
    f = t.FakeTracker(allowed_authors=["owner"])
    f.add_issue(1, "a", "", "stranger", ["factory:queued"], "2026-01-01")
    with pytest.raises(t.NotAllowlisted):
        f.transition(1, "queued", "claimed")
    assert f.labels(1) == {"factory:queued"}


def test_allowlist_case_insensitive_and_exact():
    f = t.FakeTracker(allowed_authors=["Owner"])
    assert f.is_allowed("owner") and not f.is_allowed("owner2") and not f.is_allowed("")


def test_select_claimable_skips_strangers_oldest_first():
    f = t.FakeTracker(allowed_authors=["owner"])
    f.add_issue(1, "a", "", "stranger", ["factory:queued"], "2026-01-01")
    f.add_issue(2, "b", "", "owner", ["factory:queued"], "2026-01-02")
    pick, skipped = t.select_claimable(f)
    assert pick.number == 2 and [i.number for i in skipped] == [1]


def test_select_claimable_none():
    f = t.FakeTracker(allowed_authors=["owner"])
    f.add_issue(1, "a", "", "stranger", ["factory:queued"], "2026-01-01")
    pick, skipped = t.select_claimable(f)
    assert pick is None and len(skipped) == 1


def test_fake_halt_and_count_and_comment():
    f = t.FakeTracker(allowed_authors=["owner"])
    assert not f.halt_label_present()
    f.add_issue(9, "h", "", "owner", ["factory:halt"], "2026-01-01")
    assert f.halt_label_present()
    f.add_issue(1, "a", "", "owner", ["factory:awaiting-human"], "2026-01-01")
    assert f.count_state("awaiting-human") == 1
    f.comment(1, "hi")
    assert f.comments == [(1, "hi")]


# ---------- gh ----------
def test_gh_list_queued_parses_sorts_and_uses_arg_lists():
    out = json.dumps([gh_issue(2, title=EVIL, body=EVIL), gh_issue(1)])
    r = FakeRunner([out])
    g = t.GhTracker(r, allowed_authors=["owner"])
    issues = g.list_queued()
    assert [i.number for i in issues] == [1, 2]
    assert issues[1].title == EVIL            # data is preserved, never executed
    argv = r.calls[0]
    assert argv[:3] == ["gh", "issue", "list"]
    assert "factory:queued" in argv


def test_gh_never_puts_untrusted_text_in_argv():
    out = json.dumps([gh_issue(1, title=EVIL, body=EVIL)])
    view = json.dumps(gh_issue(1, title=EVIL, body=EVIL))
    r = FakeRunner([out, view, ProcResult(0, "", "")])
    g = t.GhTracker(r, allowed_authors=["owner"])
    g.list_queued()
    g.transition(1, "queued", "claimed")
    for argv in r.calls:
        assert all(isinstance(a, str) for a in argv)
        assert not any("rm -rf" in a or "pwned" in a for a in argv)


def test_gh_transition_rechecks_state_then_edits_labels():
    view = json.dumps(gh_issue(5))
    r = FakeRunner([view, ProcResult(0, "", "")])
    g = t.GhTracker(r, allowed_authors=["owner"])
    g.transition(5, "queued", "claimed")
    assert r.calls[0][:3] == ["gh", "issue", "view"]
    edit = r.calls[1]
    assert edit[:3] == ["gh", "issue", "edit"] and edit[3] == "5"
    assert "--remove-label" in edit and "factory:queued" in edit
    assert "--add-label" in edit and "factory:claimed" in edit


def test_gh_transition_state_mismatch_does_not_edit():
    view = json.dumps(gh_issue(5, labels=("factory:building",)))
    r = FakeRunner([view])
    g = t.GhTracker(r, allowed_authors=["owner"])
    with pytest.raises(t.StateMismatch):
        g.transition(5, "queued", "claimed")
    assert len(r.calls) == 1


def test_gh_claim_refuses_non_allowlisted_without_edit():
    view = json.dumps(gh_issue(5, author="stranger"))
    r = FakeRunner([view])
    g = t.GhTracker(r, allowed_authors=["owner"])
    with pytest.raises(t.NotAllowlisted):
        g.transition(5, "queued", "claimed")
    assert len(r.calls) == 1


def test_gh_illegal_transition_makes_no_calls():
    r = FakeRunner()
    g = t.GhTracker(r, allowed_authors=["owner"])
    with pytest.raises(states.IllegalTransition):
        g.transition(5, "queued", "done")
    assert r.calls == []


def test_gh_failure_raises():
    r = FakeRunner([ProcResult(1, "", "boom")])
    g = t.GhTracker(r, allowed_authors=["owner"])
    with pytest.raises(t.TrackerError, match="boom"):
        g.list_queued()


def test_gh_bad_json_raises():
    g = t.GhTracker(FakeRunner(["not json"]), allowed_authors=["owner"])
    with pytest.raises(t.TrackerError):
        g.list_queued()


def test_gh_halt_label_and_count():
    r = FakeRunner([json.dumps([{"number": 3}]), json.dumps([{"number": 1}, {"number": 2}])])
    g = t.GhTracker(r, allowed_authors=["owner"])
    assert g.halt_label_present() is True
    assert g.count_state("awaiting-human") == 2
    assert "factory:halt" in r.calls[0] and "factory:awaiting-human" in r.calls[1]


def test_gh_comment_uses_equals_form_and_int_number():
    r = FakeRunner()
    g = t.GhTracker(r, allowed_authors=["owner"])
    g.comment(7, "--repo evil\nbody")
    argv = r.calls[0]
    assert argv[:4] == ["gh", "issue", "comment", "7"]
    assert argv[4] == "--body=--repo evil\nbody"
    with pytest.raises(TypeError):
        g.comment("7; rm", "x")


def test_gh_repo_flag_added():
    r = FakeRunner()
    g = t.GhTracker(r, allowed_authors=["owner"], repo="o/r")
    g.halt_label_present()
    assert "--repo" in r.calls[0] and "o/r" in r.calls[0]

"""Queue adapter: GitHub issues labelled `factory:*`.

Issue title and body are untrusted text. They are carried as data and never
placed in argv, a shell string, or a comment we author.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import states
from .proc import ProcResult, run as default_run


class TrackerError(RuntimeError):
    pass


class NotAllowlisted(TrackerError):
    pass


class StateMismatch(TrackerError):
    pass


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    author: str
    labels: Tuple[str, ...]
    created_at: str


class Tracker:
    """Interface. Subclasses implement the raw reads and writes."""

    def __init__(self, allowed_authors: Iterable[str]):
        self._allowed = {a.strip().lower() for a in allowed_authors if a and a.strip()}

    def is_allowed(self, author: str) -> bool:
        return bool(author) and author.strip().lower() in self._allowed

    def _authorize_claim(self, current: str, new: str, author: str) -> None:
        if new == "claimed" and not self.is_allowed(author):
            raise NotAllowlisted(f"author {author!r} is not in the allowlist")

    def list_queued(self) -> List[Issue]:
        raise NotImplementedError

    def halt_label_present(self) -> bool:
        raise NotImplementedError

    def count_state(self, state: str) -> int:
        raise NotImplementedError

    def transition(self, number: int, current: str, new: str) -> None:
        raise NotImplementedError

    def comment(self, number: int, body: str) -> None:
        raise NotImplementedError


def select_claimable(tracker: Tracker) -> Tuple[Optional[Issue], List[Issue]]:
    """Oldest queued issue by an allowlisted author, plus the ones skipped."""
    skipped: List[Issue] = []
    for issue in tracker.list_queued():
        if tracker.is_allowed(issue.author):
            return issue, skipped
        skipped.append(issue)
    return None, skipped


class FakeTracker(Tracker):
    def __init__(self, allowed_authors: Iterable[str]):
        super().__init__(allowed_authors)
        self._issues: Dict[int, dict] = {}
        self.comments: List[Tuple[int, str]] = []
        self.transitions: List[Tuple[int, str, str]] = []

    def add_issue(self, number, title, body, author, labels, created_at):
        self._issues[number] = dict(title=title, body=body, author=author,
                                    labels=set(labels), created_at=created_at)

    def labels(self, number) -> Set[str]:
        return set(self._issues[number]["labels"])

    def _issue(self, n) -> Issue:
        d = self._issues[n]
        return Issue(n, d["title"], d["body"], d["author"], tuple(sorted(d["labels"])), d["created_at"])

    def list_queued(self):
        out = [self._issue(n) for n, d in self._issues.items() if states.label("queued") in d["labels"]]
        return sorted(out, key=lambda i: (i.created_at, i.number))

    def halt_label_present(self):
        return any(states.HALT_LABEL in d["labels"] for d in self._issues.values())

    def count_state(self, state):
        return sum(1 for d in self._issues.values() if states.label(state) in d["labels"])

    def transition(self, number, current, new):
        states.check_transition(current, new)
        d = self._issues[number]
        if states.state_of(d["labels"]) != current:
            raise StateMismatch(f"issue {number} is not in state {current}")
        self._authorize_claim(current, new, d["author"])
        d["labels"].discard(states.label(current))
        d["labels"].add(states.label(new))
        self.transitions.append((number, current, new))

    def comment(self, number, body):
        self.comments.append((number, body))


Runner = Callable[..., ProcResult]


class GhTracker(Tracker):
    def __init__(self, runner: Runner = default_run, allowed_authors: Iterable[str] = (),
                 repo: Optional[str] = None):
        super().__init__(allowed_authors)
        self._run = runner
        self._repo = repo

    def _gh(self, args: Sequence[str]) -> str:
        argv = ["gh"] + list(args)
        if self._repo:
            argv += ["--repo", self._repo]
        r = self._run(argv, timeout=60)
        if r.returncode != 0:
            raise TrackerError(f"gh failed ({r.returncode}): {r.stderr.strip()}")
        return r.stdout

    def _json(self, args):
        try:
            return json.loads(self._gh(args))
        except ValueError as e:
            raise TrackerError(f"gh returned invalid JSON: {e}") from e

    @staticmethod
    def _issue(d) -> Issue:
        try:
            return Issue(int(d["number"]), str(d.get("title", "")), str(d.get("body", "")),
                         str((d.get("author") or {}).get("login", "")),
                         tuple(x["name"] for x in d.get("labels", [])), str(d.get("createdAt", "")))
        except (KeyError, TypeError, ValueError) as e:
            raise TrackerError(f"unexpected gh issue shape: {e}") from e

    def list_queued(self):
        data = self._json(["issue", "list", "--state", "open", "--label", states.label("queued"),
                           "--limit", "1000", "--json", "number,title,body,author,labels,createdAt"])
        return sorted((self._issue(d) for d in data), key=lambda i: (i.created_at, i.number))

    def _count(self, label: str) -> int:
        data = self._json(["issue", "list", "--state", "open", "--label", label,
                           "--limit", "1000", "--json", "number"])
        return len(data)

    def halt_label_present(self):
        return self._count(states.HALT_LABEL) > 0

    def count_state(self, state):
        if state not in states.STATES:
            raise ValueError(f"unknown state {state!r}")
        return self._count(states.label(state))

    def transition(self, number, current, new):
        if isinstance(number, bool) or not isinstance(number, int):
            raise TypeError("issue number must be an int")
        states.check_transition(current, new)
        issue = self._issue(self._json(["issue", "view", str(number),
                                        "--json", "number,title,body,author,labels,createdAt"]))
        if states.state_of(issue.labels) != current:
            raise StateMismatch(f"issue {number} is not in state {current}")
        self._authorize_claim(current, new, issue.author)
        self._gh(["issue", "edit", str(number), "--remove-label", states.label(current),
                  "--add-label", states.label(new)])

    def comment(self, number, body):
        if isinstance(number, bool) or not isinstance(number, int):
            raise TypeError("issue number must be an int")
        self._gh(["issue", "comment", str(number), f"--body={body}"])

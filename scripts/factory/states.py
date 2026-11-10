"""State machine over the `factory:*` issue labels."""
from __future__ import annotations

from typing import Iterable, Optional

PREFIX = "factory:"
HALT_LABEL = PREFIX + "halt"
STATES = ("proposed", "queued", "claimed", "building", "verifying", "merge-ready",
          "done", "awaiting-human", "failed")

TRANSITIONS = {
    "proposed": {"queued"},
    "queued": {"claimed"},
    "claimed": {"building", "awaiting-human", "failed"},
    "building": {"verifying", "awaiting-human", "failed"},
    "verifying": {"merge-ready", "awaiting-human", "failed"},
    "merge-ready": {"done", "awaiting-human"},
    "awaiting-human": {"queued", "done"},   # a person relabels or merges by hand
    "failed": {"queued"},                    # a person requeues
    "done": set(),
}


class IllegalTransition(ValueError):
    pass


def label(state: str) -> str:
    return PREFIX + state


def state_from_label(lbl: str) -> Optional[str]:
    if lbl.startswith(PREFIX) and lbl[len(PREFIX):] in STATES:
        return lbl[len(PREFIX):]
    return None


def state_of(labels: Iterable[str]) -> str:
    found = [s for s in (state_from_label(x) for x in labels) if s]
    if len(found) != 1:
        raise IllegalTransition(f"expected exactly one factory state label, found {found}")
    return found[0]


def check_transition(current: str, new: str) -> None:
    if current not in TRANSITIONS or new not in TRANSITIONS:
        raise IllegalTransition(f"unknown state in {current!r} -> {new!r}")
    if new not in TRANSITIONS[current]:
        raise IllegalTransition(f"illegal transition {current} -> {new}")

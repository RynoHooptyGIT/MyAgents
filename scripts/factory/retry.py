"""Retry ladder. Round 1: same model plus gate output. Round 2: a different model,
failing text only. Then a person. A retry identical in model and input is refused."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .policy import Policy

MAX_FAILURE_CHARS = 4000
_FAIL_LINE = re.compile(r"(FAIL|ERROR|Error|assert|^E\s|Traceback|Exception)")


class IdenticalRetry(RuntimeError):
    pass


@dataclass(frozen=True)
class Attempt:
    round: int
    model: str
    input_hash: str


@dataclass(frozen=True)
class Plan:
    round: int
    model: str
    context: str


def _hash(model: str, context: str) -> str:
    return hashlib.sha256((model + "\0" + context).encode("utf-8")).hexdigest()


def attempt_record(round_no: int, model: str, context: str) -> Attempt:
    return Attempt(round_no, model, _hash(model, context))


def extract_failures(output: str) -> str:
    if not output:
        return ""
    lines = output.splitlines()
    hits = [l for l in lines if _FAIL_LINE.search(l)]
    picked = hits if hits else lines[-40:]
    text = "\n".join(picked)
    return text[-MAX_FAILURE_CHARS:] if len(text) > MAX_FAILURE_CHARS else text


def check_not_identical(history: Sequence[Attempt], model: str, context: str) -> None:
    h = _hash(model, context)
    for a in history:
        if a.model == model and a.input_hash == h:
            raise IdenticalRetry(f"retry identical to round {a.round} (same model and input)")


class Ladder:
    def __init__(self, policy: Policy):
        self._policy = policy

    def next_attempt(self, history: List[Attempt], gate_output: str) -> Optional[Plan]:
        if not history:
            raise ValueError("history must include the initial attempt")
        last = history[-1].round
        if last >= self._policy.max_rounds:
            return None
        if last == 0:
            plan = Plan(1, history[0].model, gate_output)
        else:
            plan = Plan(2, self._policy.routing["retry_round_2"], extract_failures(gate_output))
        check_not_identical(history, plan.model, plan.context)
        return plan

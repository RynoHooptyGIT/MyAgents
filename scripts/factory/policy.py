"""Load and validate .factory/policy.yaml. Missing or malformed is an error."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from . import miniyaml

ROLES = ("orchestration", "triage", "mechanical", "spec", "build",
         "sealed_test_author", "verifier", "retry_round_2", "t2_design")
REQUIRED_PROTECTED = ("scripts/factory/**", ".factory/policy.yaml")
TOP_KEYS = {"version", "tiers", "protected_paths", "t0_paths", "dependency_files", "size",
            "autonomy", "budget", "queue", "retries", "allowlisted_authors", "routing"}
TIERS = ("T0", "T1", "T2")


class PolicyError(ValueError):
    pass


@dataclass(frozen=True)
class Policy:
    protected_paths: Tuple[str, ...]
    t0_paths: Tuple[str, ...]
    dependency_files: Tuple[str, ...]
    max_diff_lines: int
    max_deleted_files: int
    promotion_count: int
    revert_window_days: int
    per_issue_usd: float
    per_day_usd: float
    max_awaiting_human: int
    max_open_proposals: int
    max_rounds: int
    allowlisted_authors: Tuple[str, ...]
    routing: Dict[str, str]


def _section(d, key, keys):
    if key not in d:
        raise PolicyError(f"policy: missing section {key!r}")
    s = d[key]
    if not isinstance(s, dict):
        raise PolicyError(f"policy: {key!r} must be a map")
    missing = [k for k in keys if k not in s]
    if missing:
        raise PolicyError(f"policy: {key!r} missing {missing}")
    extra = [k for k in s if k not in keys]
    if extra:
        raise PolicyError(f"policy: unknown keys in {key!r}: {extra}")
    return s


def _pos_int(v, name, minimum=1):
    if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
        raise PolicyError(f"policy: {name} must be an integer >= {minimum}")
    return v


def _pos_num(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        raise PolicyError(f"policy: {name} must be a positive number")
    return float(v)


def _str_list(d, key):
    if key not in d:
        raise PolicyError(f"policy: missing {key!r}")
    v = d[key]
    if (not isinstance(v, list) or not v
            or not all(isinstance(x, str) and x.strip() for x in v)):
        raise PolicyError(f"policy: {key!r} must be a non-empty list of strings")
    return tuple(v)


def from_dict(d) -> Policy:
    if not isinstance(d, dict):
        raise PolicyError("policy: top level must be a map")
    for key in sorted(TOP_KEYS):
        if key not in d:
            raise PolicyError(f"policy: missing {key!r}")
    extra = [k for k in d if k not in TOP_KEYS]
    if extra:
        raise PolicyError(f"policy: unknown top-level keys: {extra}")
    if d["version"] != 1 or isinstance(d["version"], bool):
        raise PolicyError("policy: unsupported version (expected 1)")
    tiers = d["tiers"]
    if not isinstance(tiers, dict) or set(tiers) != set(TIERS):
        raise PolicyError(f"policy: 'tiers' must define exactly {list(TIERS)}")

    protected = _str_list(d, "protected_paths")
    for needed in REQUIRED_PROTECTED:
        if needed not in protected:
            raise PolicyError(f"policy: protected_paths must include {needed!r}")
    t0 = _str_list(d, "t0_paths")
    deps = _str_list(d, "dependency_files")
    authors = _str_list(d, "allowlisted_authors")

    size = _section(d, "size", ("max_diff_lines", "max_deleted_files"))
    auto = _section(d, "autonomy", ("promotion_count", "revert_window_days"))
    budget = _section(d, "budget", ("per_issue_usd", "per_day_usd"))
    queue = _section(d, "queue", ("max_awaiting_human", "max_open_proposals"))
    retries = _section(d, "retries", ("max_rounds",))
    routing = _section(d, "routing", ROLES)
    for role, model in routing.items():
        if not isinstance(model, str) or not model.strip():
            raise PolicyError(f"policy: routing.{role} must be a non-empty string")
    if routing["verifier"] == routing["build"]:
        raise PolicyError("policy: routing.verifier must differ from routing.build")
    if routing["retry_round_2"] == routing["build"]:
        raise PolicyError("policy: routing.retry_round_2 must differ from routing.build")
    if _pos_int(retries["max_rounds"], "retries.max_rounds") != 2:
        raise PolicyError("policy: retries.max_rounds must be 2 (the ladder has two rounds)")

    per_issue = _pos_num(budget["per_issue_usd"], "budget.per_issue_usd")
    per_day = _pos_num(budget["per_day_usd"], "budget.per_day_usd")
    if per_issue > per_day:
        raise PolicyError("policy: budget.per_issue_usd cannot exceed per_day_usd")

    return Policy(
        protected_paths=protected, t0_paths=t0, dependency_files=deps,
        max_diff_lines=_pos_int(size["max_diff_lines"], "size.max_diff_lines"),
        max_deleted_files=_pos_int(size["max_deleted_files"], "size.max_deleted_files", 0),
        promotion_count=_pos_int(auto["promotion_count"], "autonomy.promotion_count"),
        revert_window_days=_pos_int(auto["revert_window_days"], "autonomy.revert_window_days"),
        per_issue_usd=per_issue, per_day_usd=per_day,
        max_awaiting_human=_pos_int(queue["max_awaiting_human"], "queue.max_awaiting_human"),
        max_open_proposals=_pos_int(queue["max_open_proposals"], "queue.max_open_proposals"),
        max_rounds=2, allowlisted_authors=authors, routing=dict(routing),
    )


def policy_path(root) -> Path:
    return Path(root) / ".factory" / "policy.yaml"


def load(root) -> Policy:
    path = policy_path(root)
    if not path.is_file():
        raise PolicyError(f"policy file missing: {path}")
    try:
        data = miniyaml.parse(path.read_text(encoding="utf-8"))
    except (miniyaml.YamlError, UnicodeDecodeError, OSError) as e:
        raise PolicyError(f"policy file malformed: {path}: {e}") from e
    return from_dict(data)

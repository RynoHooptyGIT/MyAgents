#!/usr/bin/env python3
"""Cost gate for model routing: estimate a task's cost per model and pick one.

Usage:
  estimate.py --in 40000 --out 8000 --tier standard [--config PATH] [--json]
  estimate.py --in 40000 --out 8000 --model sonnet

Exit: 0 proceed (or confirm-level, verdict printed) · 3 blocked by budget · 1 bad input
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cost(model, tokens_in, tokens_out):
    return (tokens_in * model["input"] + tokens_out * model["output"]) / 1_000_000


def choose(cfg, tier):
    """Cheapest model whose tier rank is >= the required tier; ties by price."""
    ranks = {t: i for i, t in enumerate(cfg["tiers"])}
    if tier not in ranks:
        raise ValueError(f"unknown tier {tier!r}; expected one of {cfg['tiers']}")
    fits = [(m["input"] + m["output"], name) for name, m in cfg["models"].items()
            if ranks[m["tier"]] >= ranks[tier]]
    if not fits:
        raise ValueError(f"no model at tier {tier} or above")
    # Lowest tier first, then cheapest, so the router stays frugal.
    fits.sort(key=lambda f: (ranks[cfg["models"][f[1]]["tier"]], f[0]))
    return fits[0][1]


def verdict(usd, budget):
    if usd >= float(budget["block_above_usd"]):
        return "block"
    if usd >= float(budget["confirm_above_usd"]):
        return "confirm"
    return "ok"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--in", dest="tin", type=int, required=True, help="estimated input tokens")
    ap.add_argument("--out", dest="tout", type=int, required=True, help="estimated output tokens")
    ap.add_argument("--tier", help="required tier; router picks the cheapest adequate model")
    ap.add_argument("--model", help="force a model (cost-check only)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    cfg_path = a.config or next(
        (p for p in (Path(".agents/model-routing.json"), ROOT / "templates/model-routing.json") if p.exists()), None)
    if not cfg_path:
        print("no model-routing.json found", file=sys.stderr)
        return 1
    cfg = load_config(cfg_path)
    try:
        name = a.model or choose(cfg, a.tier or "standard")
        model = cfg["models"][name]
    except (KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    usd = cost(model, a.tin, a.tout)
    v = verdict(usd, cfg["budget"])
    table = {n: round(cost(m, a.tin, a.tout), 4) for n, m in cfg["models"].items()}
    out = {"model": name, "estimated_usd": round(usd, 4), "verdict": v,
           "all_models_usd": table, "prices_verified": bool(cfg.get("prices_verified"))}
    if a.json:
        print(json.dumps(out))
    else:
        print(f"model={name} est=${usd:.4f} verdict={v}")
        print("compare: " + " ".join(f"{n}=${c:.4f}" for n, c in table.items()))
        if not out["prices_verified"]:
            print("warning: prices_verified is false; set real prices in .agents/model-routing.json")
    return 3 if v == "block" else 0


if __name__ == "__main__":
    sys.exit(main())

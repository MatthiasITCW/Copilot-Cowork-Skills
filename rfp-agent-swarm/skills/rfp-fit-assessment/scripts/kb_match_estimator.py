#!/usr/bin/env python3
"""kb_match_estimator.py

Estimates the expected answer-bank match rate for a classified RFP task
list PRIOR to running `rfp-respond`. Feeds the "KB Match Rate" dimension
(weight 25%) of the fit scorecard.

This is explicitly an ESTIMATE. True match rate is only known after
`rfp-respond` actually runs against the answer bank.

Algorithm (deterministic, stdlib only):
  For each classified question category c:
    historical_rate_c = bank_stats.category_rates[c]
                        (fall back to defaults below)
    contribution_c    = question_count_c * historical_rate_c
  overall = sum(contribution_c) / total_questions
  confidence:
    HIGH   if >=80% of questions hit categories with >=30 historical samples
    MEDIUM if >=50%
    LOW    otherwise

INPUT task-list (produced by rfp-intake):
{
  "rfp_id": "...",
  "total_questions": 142,
  "categories": {
    "security":      {"count": 24},
    "legal":         {"count": 12},
    "technical":     {"count": 56},
    "commercial":    {"count": 8},
    "implementation":{"count": 22},
    "references":    {"count": 10},
    "product":       {"count": 6},
    "other":         {"count": 4}
  }
}

INPUT bank-stats (produced by rfp-answer-bank):
{
  "category_rates": {
    "security":      {"rate": 0.82, "samples": 212},
    "legal":         {"rate": 0.74, "samples": 148},
    ...
  },
  "generated_at": "..."
}

OUTPUT (kb_match_estimate.json):
{
  "rfp_id": "...",
  "overall_estimate_pct": 68,
  "by_category": {
     "security": {"count": 24, "rate": 0.82, "expected_hits": 19.7, "samples": 212},
     ...
  },
  "confidence": "MEDIUM",
  "notes": "...",
  "generated_at": "..."
}

Stdlib only. JSON to stdout (and optional file).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Fallback defaults when bank_stats is thin.
DEFAULT_RATES: dict[str, float] = {
    "security": 0.75,
    "legal": 0.65,
    "technical": 0.70,
    "commercial": 0.60,
    "implementation": 0.55,
    "references": 0.80,
    "product": 0.85,
    "other": 0.40,
}

SAMPLES_HIGH = 30  # category with >= this many historical answers is "reliable"


def _fail(message: str, code: int = 2) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        _fail(f"{label} not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        _fail(f"{label} JSON invalid: {exc}")
    if not isinstance(data, dict):
        _fail(f"{label} must be a JSON object")
    return data


def _normalise_task_list(data: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Return {category: {"count": int}}.

    Accepts either the canonical schema {categories: {...}} or a flat
    {category_counts: {...}} fallback.
    """
    if "categories" in data and isinstance(data["categories"], dict):
        cats = {}
        for cat, payload in data["categories"].items():
            if isinstance(payload, dict) and "count" in payload:
                cats[cat] = {"count": int(payload["count"])}
            elif isinstance(payload, (int, float)):
                cats[cat] = {"count": int(payload)}
        return cats
    if "category_counts" in data and isinstance(data["category_counts"], dict):
        return {c: {"count": int(n)} for c, n in data["category_counts"].items()}
    _fail("task-list missing 'categories' or 'category_counts'")
    return {}  # unreachable


def estimate(
    task_list: dict[str, Any], bank_stats: dict[str, Any]
) -> dict[str, Any]:
    cats = _normalise_task_list(task_list)
    total_questions = sum(c["count"] for c in cats.values())
    if total_questions <= 0:
        _fail("task-list has zero questions")

    rates = (bank_stats.get("category_rates") or {}) if bank_stats else {}

    by_category: dict[str, dict[str, Any]] = {}
    expected_hits_total = 0.0
    reliable_count_covered = 0

    for cat, payload in cats.items():
        count = payload["count"]
        entry = rates.get(cat) or {}
        if "rate" in entry:
            rate = float(entry["rate"])
        else:
            rate = DEFAULT_RATES.get(cat, DEFAULT_RATES["other"])
        samples = int(entry.get("samples", 0))
        expected = round(count * rate, 1)
        expected_hits_total += expected
        if samples >= SAMPLES_HIGH:
            reliable_count_covered += count
        by_category[cat] = {
            "count": count,
            "rate": round(rate, 3),
            "expected_hits": expected,
            "samples": samples,
            "source": "bank_stats" if "rate" in entry else "default",
        }

    overall_pct = int(round(100.0 * expected_hits_total / total_questions))

    coverage = reliable_count_covered / total_questions
    if coverage >= 0.8:
        confidence = "HIGH"
    elif coverage >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    notes_parts = []
    if confidence == "LOW":
        notes_parts.append(
            "Low historical coverage; treat estimate as provisional."
        )
    default_only = [
        c for c, v in by_category.items() if v["source"] == "default"
    ]
    if default_only:
        notes_parts.append(
            "Using default rates for: " + ", ".join(sorted(default_only))
        )
    notes_parts.append(
        "ESTIMATE ONLY — true match rate known only after rfp-respond."
    )

    return {
        "rfp_id": task_list.get("rfp_id", "unknown"),
        "overall_estimate_pct": overall_pct,
        "by_category": by_category,
        "confidence": confidence,
        "notes": " ".join(notes_parts),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate answer-bank match rate for an RFP task list."
    )
    parser.add_argument(
        "--task-list",
        required=True,
        type=Path,
        help="Path to task_list.json from rfp-intake.",
    )
    parser.add_argument(
        "--bank-stats",
        required=True,
        type=Path,
        help="Path to bank_stats.json from rfp-answer-bank.",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Optional output JSON file."
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output."
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    task_list = _load_json(args.task_list, "task-list")
    bank_stats = _load_json(args.bank_stats, "bank-stats")
    result = estimate(task_list, bank_stats)
    indent = 2 if args.pretty else None
    payload = json.dumps(result, indent=indent, sort_keys=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

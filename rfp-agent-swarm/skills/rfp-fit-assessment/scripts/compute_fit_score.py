#!/usr/bin/env python3
"""compute_fit_score.py

Deterministic weighted scorecard computation for the RFP Fit Assessment
(Step 2 of the RFP Agent Swarm). Reads a scorecard JSON, validates
weights sum to 100, computes per-dimension contributions and the overall
weighted total on a 0.0-100.0 scale, emits a recommendation band
(Go / Conditional / No-Go), and surfaces any kill-criteria flags.

The system does NOT decide. The output is advisory. A named human owner
signs the resulting memo.

INPUT schema (scorecard.json):
{
  "rfp_id": "ACME-2026-05-20",
  "weights": {                # MUST sum to 100
    "kb_match": 25,
    "technical_fit": 20,
    "commercial_fit": 15,
    "competitive": 10,
    "strategic": 10,
    "resource": 10,
    "deadline": 10
  },
  "scores": {                 # raw 0-5 per dimension
    "kb_match": 4,
    "technical_fit": 4,
    "commercial_fit": 3,
    "competitive": 3,
    "strategic": 4,
    "resource": 3,
    "deadline": 3
  },
  "evidence": {
    "kb_match": "Est 68%, MEDIUM confidence",
    "technical_fit": "All must-have features supported",
    ...
  },
  "kill_criteria": [
    {"id": "missing_cert", "description": "FedRAMP High required",
     "fired": false}
  ]
}

OUTPUT (fit_result.json):
{
  "rfp_id": "...",
  "weighted_total": 71.0,
  "band": "CONDITIONAL",
  "recommendation": "ADVISORY_ONLY - human decides",
  "contributions": [
    {"dimension": "kb_match", "raw": 4, "value": 80,
     "weight": 25, "contribution": 20.0, "evidence": "..."}
    ...
  ],
  "risks": [ ... ],
  "kill_criteria_flagged": [ ... ],
  "generated_at": "..."
}

Python 3 stdlib only. No network. Exits non-zero on validation failure.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIMENSIONS = [
    "kb_match",
    "technical_fit",
    "commercial_fit",
    "competitive",
    "strategic",
    "resource",
    "deadline",
]

DEFAULT_WEIGHTS = {
    "kb_match": 25,
    "technical_fit": 20,
    "commercial_fit": 15,
    "competitive": 10,
    "strategic": 10,
    "resource": 10,
    "deadline": 10,
}

BAND_GO = 75.0
BAND_CONDITIONAL = 50.0


def _fail(message: str, code: int = 2) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def load_scorecard(path: Path) -> dict[str, Any]:
    if not path.exists():
        _fail(f"scorecard not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        _fail(f"scorecard JSON invalid: {exc}")
    if not isinstance(data, dict):
        _fail("scorecard must be a JSON object")
    return data


def validate(scorecard: dict[str, Any]) -> None:
    weights = scorecard.get("weights") or DEFAULT_WEIGHTS
    scores = scorecard.get("scores") or {}

    # Dimension presence
    missing_w = [d for d in DIMENSIONS if d not in weights]
    missing_s = [d for d in DIMENSIONS if d not in scores]
    if missing_w:
        _fail(f"weights missing dimensions: {missing_w}")
    if missing_s:
        _fail(f"scores missing dimensions: {missing_s}")

    # Weight sum = 100
    total = sum(int(weights[d]) for d in DIMENSIONS)
    if total != 100:
        _fail(
            "weights do not sum to 100 "
            f"(got {total}); refusing to silently normalise"
        )

    # Score range 0-5
    for d in DIMENSIONS:
        raw = scores[d]
        if not isinstance(raw, (int, float)):
            _fail(f"score for {d} must be numeric")
        if raw < 0 or raw > 5:
            _fail(f"score for {d} out of range 0-5: {raw}")

    # Evidence required for extreme scores
    evidence = scorecard.get("evidence", {}) or {}
    for d in DIMENSIONS:
        raw = scores[d]
        if raw in (0, 1, 5):
            if not str(evidence.get(d, "")).strip():
                _fail(
                    f"evidence required for {d} at raw={raw} "
                    "(scores 0, 1, 5 must include evidence)"
                )


def band_for(total: float) -> str:
    if total >= BAND_GO:
        return "GO"
    if total >= BAND_CONDITIONAL:
        return "CONDITIONAL"
    return "NO_GO"


def compute(scorecard: dict[str, Any]) -> dict[str, Any]:
    weights = scorecard.get("weights") or DEFAULT_WEIGHTS
    scores = scorecard["scores"]
    evidence = scorecard.get("evidence", {}) or {}

    contributions: list[dict[str, Any]] = []
    total = 0.0
    risks: list[dict[str, Any]] = []

    for dim in DIMENSIONS:
        raw = float(scores[dim])
        value = raw * 20.0  # 0-5 -> 0-100
        weight = float(weights[dim])
        contribution = round(value * weight / 100.0, 2)
        total += contribution
        ev = str(evidence.get(dim, "")).strip()
        contributions.append(
            {
                "dimension": dim,
                "raw": raw,
                "value": round(value, 1),
                "weight": weight,
                "contribution": contribution,
                "evidence": ev,
            }
        )
        if raw <= 2:
            risks.append(
                {
                    "dimension": dim,
                    "raw": raw,
                    "note": ev or "Low score — no evidence captured",
                    "severity": "HIGH" if raw <= 1 else "MEDIUM",
                }
            )

    weighted_total = round(total, 1)

    # Kill criteria
    killed = []
    for item in scorecard.get("kill_criteria", []) or []:
        if item.get("fired"):
            killed.append(
                {
                    "id": item.get("id", "unknown"),
                    "description": item.get("description", ""),
                }
            )

    result: dict[str, Any] = {
        "rfp_id": scorecard.get("rfp_id", "unknown"),
        "weighted_total": weighted_total,
        "band": band_for(weighted_total),
        "recommendation": "ADVISORY_ONLY - human decides",
        "contributions": contributions,
        "risks": risks,
        "kill_criteria_flagged": killed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute weighted RFP fit score (advisory only)."
    )
    parser.add_argument(
        "--scorecard",
        required=True,
        type=Path,
        help="Path to scorecard.json input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path. If omitted, result is printed to stdout.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (indent=2).",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    scorecard = load_scorecard(args.scorecard)
    validate(scorecard)
    result = compute(scorecard)
    indent = 2 if args.pretty else None
    payload = json.dumps(result, indent=indent, sort_keys=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

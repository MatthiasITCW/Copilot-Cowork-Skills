#!/usr/bin/env python3
"""
generate_analytics_report.py
----------------------------

Compute the numbers for the RFP Agent Swarm analytics report and emit a JSON
structure that the docx or pptx renderer will consume.

All arithmetic is performed in this script — never rely on the language model
for numeric aggregation.

CLI:
    python scripts/generate_analytics_report.py \\
        --responses working/reviewed_responses.json \\
        --gate-audit working/gate_audit.json \\
        --corrections working/corrections.json \\
        --metadata working/rfp_metadata.json \\
        --output working/analytics_report.json \\
        [--history working/rfp_history.json] \\
        [--baseline-minutes 15]

Exit codes:
    0  report written
    2  input validation failure
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import statistics
import sys
from typing import Any, Dict, List


DEFAULT_BASELINE_MINUTES = 15


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute analytics report JSON.")
    p.add_argument("--responses", required=True)
    p.add_argument("--gate-audit", required=True)
    p.add_argument("--corrections", required=True)
    p.add_argument("--metadata", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--history", required=False, default="")
    p.add_argument("--baseline-minutes", type=int,
                   default=DEFAULT_BASELINE_MINUTES)
    return p.parse_args()


def load_json(path: str, default: Any = None) -> Any:
    if not path or not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def fail(code: int, msg: str) -> None:
    sys.stderr.write("ERROR: " + msg + "\n")
    sys.exit(code)


def compute_tier_counts(responses: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for r in responses:
        tier = r.get("tier")
        if tier in counts:
            counts[tier] += 1
    return counts


def compute_match_rate(tier_counts: Dict[str, int]) -> Dict[str, float]:
    total = sum(tier_counts.values())
    if total == 0:
        return {"HIGH_pct": 0.0, "MEDIUM_pct": 0.0, "LOW_pct": 0.0,
                "match_rate_pct": 0.0}
    high = tier_counts["HIGH"] / total
    medium = tier_counts["MEDIUM"] / total
    low = tier_counts["LOW"] / total
    return {
        "HIGH_pct": round(high * 100, 2),
        "MEDIUM_pct": round(medium * 100, 2),
        "LOW_pct": round(low * 100, 2),
        "match_rate_pct": round((high + medium) * 100, 2),
    }


def compute_by_category(
    responses: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for r in responses:
        cat = r.get("category", "Other")
        bucket = out.setdefault(
            cat, {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}
        )
        bucket["total"] += 1
        tier = r.get("tier")
        if tier in ("HIGH", "MEDIUM", "LOW"):
            bucket[tier] += 1
    return out


def compute_gate_outcomes(
    gate_audit: List[Dict[str, Any]],
) -> Dict[str, Any]:
    pass_count = 0
    reject_count = 0
    gates: List[Dict[str, Any]] = []
    for g in gate_audit:
        outcome = g.get("outcome", "").lower()
        if outcome == "approved":
            pass_count += 1
        elif outcome == "rejected":
            reject_count += 1
        gates.append({
            "gate": g.get("gate"),
            "approver": g.get("approver"),
            "timestamp": g.get("timestamp"),
            "outcome": g.get("outcome"),
        })
    return {
        "pass_count": pass_count,
        "reject_count": reject_count,
        "gates": gates,
    }


def compute_effort_metrics(
    responses: List[Dict[str, Any]],
    baseline_minutes: int,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    total = len(responses)
    kb_matched = sum(
        1 for r in responses if r.get("tier") in ("HIGH", "MEDIUM")
    )
    generated = sum(1 for r in responses if r.get("tier") == "LOW")
    minutes_saved = kb_matched * baseline_minutes
    hours_saved = round(minutes_saved / 60.0, 1)

    ingest_time = metadata.get("ingest_time")
    submit_time = metadata.get("submission_time") or metadata.get("submit_time")
    turnaround_hours = None
    if ingest_time and submit_time:
        try:
            start = datetime.datetime.fromisoformat(
                ingest_time.replace("Z", "+00:00")
            )
            end = datetime.datetime.fromisoformat(
                submit_time.replace("Z", "+00:00")
            )
            delta = end - start
            turnaround_hours = round(delta.total_seconds() / 3600.0, 1)
        except (TypeError, ValueError):
            turnaround_hours = None

    return {
        "total_questions": total,
        "kb_matched": kb_matched,
        "generated": generated,
        "baseline_minutes_per_question": baseline_minutes,
        "sme_minutes_saved": minutes_saved,
        "sme_hours_saved": hours_saved,
        "turnaround_hours": turnaround_hours,
    }


def compute_learning_loop_stats(
    corrections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    new_entries = sum(
        1 for c in corrections if c.get("action") == "new_entry"
    )
    updates = sum(
        1 for c in corrections if c.get("action") == "update"
    )
    deltas: List[float] = []
    for c in corrections:
        old_conf = c.get("old_confidence")
        new_conf = c.get("new_confidence")
        if isinstance(old_conf, (int, float)) and isinstance(new_conf, (int, float)):
            deltas.append(float(new_conf) - float(old_conf))
    avg_delta = round(statistics.fmean(deltas), 3) if deltas else 0.0
    return {
        "new_kb_entries": new_entries,
        "existing_entries_updated": updates,
        "corrections_total": len(corrections),
        "avg_confidence_delta": avg_delta,
    }


def compute_provenance_audit(
    responses: List[Dict[str, Any]],
) -> Dict[str, Any]:
    kb_matched = sum(
        1 for r in responses
        if isinstance(r.get("source"), str)
        and r["source"].startswith("bank_entry:")
    )
    generated_reviewed = sum(
        1 for r in responses if r.get("source") == "generated+reviewed"
    )
    return {
        "total_rows": len(responses),
        "kb_matched_rows": kb_matched,
        "generated_reviewed_rows": generated_reviewed,
        "integrity_ok": (kb_matched + generated_reviewed) == len(responses),
    }


def compute_trend(
    history: List[Dict[str, Any]],
    current_summary: Dict[str, Any],
) -> Dict[str, Any]:
    if not history:
        return {
            "has_history": False,
            "note": "Trend data will appear after 2+ RFPs.",
        }
    series = history[-5:]  # last 5
    return {
        "has_history": True,
        "series": series,
        "current": current_summary,
    }


def write_markdown_summary(report: Dict[str, Any]) -> None:
    """Emit a short markdown summary to stderr for human visibility."""
    match = report["match_rate"]
    effort = report["effort_metrics"]
    gates = report["gate_outcomes"]
    lines = [
        "# Analytics Report Summary",
        "",
        "| Metric | Value |",
        "|:---|---:|",
        "| Total questions | {0} |".format(effort["total_questions"]),
        "| Match rate | {0}% |".format(match["match_rate_pct"]),
        "| HIGH | {0}% |".format(match["HIGH_pct"]),
        "| MEDIUM | {0}% |".format(match["MEDIUM_pct"]),
        "| LOW | {0}% |".format(match["LOW_pct"]),
        "| SME hours saved | {0} |".format(effort["sme_hours_saved"]),
        "| Gate passes | {0} |".format(gates["pass_count"]),
        "| Gate rejections | {0} |".format(gates["reject_count"]),
    ]
    sys.stderr.write("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()

    responses = load_json(args.responses, default=[])
    if not isinstance(responses, list) or not responses:
        fail(2, "responses must be a non-empty list")

    gate_audit = load_json(args.gate_audit, default=[])
    if not isinstance(gate_audit, list):
        fail(2, "gate audit must be a list")

    corrections = load_json(args.corrections, default=[])
    if not isinstance(corrections, list):
        corrections = []

    metadata = load_json(args.metadata, default={}) or {}

    history = load_json(args.history, default=[]) or []

    tier_counts = compute_tier_counts(responses)
    match_rate = compute_match_rate(tier_counts)
    by_category = compute_by_category(responses)
    gate_outcomes = compute_gate_outcomes(gate_audit)
    effort = compute_effort_metrics(responses, args.baseline_minutes, metadata)
    learning = compute_learning_loop_stats(corrections)
    provenance = compute_provenance_audit(responses)

    current_summary = {
        "rfp_id": metadata.get("rfp_id"),
        "match_rate_pct": match_rate["match_rate_pct"],
        "sme_hours_saved": effort["sme_hours_saved"],
        "turnaround_hours": effort["turnaround_hours"],
        "gate_rejections": gate_outcomes["reject_count"],
    }
    trend = compute_trend(history, current_summary)

    report = {
        "schema_version": "1.0",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "rfp": {
            "id": metadata.get("rfp_id"),
            "buyer": metadata.get("buyer_name"),
            "submission_date": metadata.get("submission_date"),
        },
        "tier_counts": tier_counts,
        "match_rate": match_rate,
        "by_category": by_category,
        "gate_outcomes": gate_outcomes,
        "effort_metrics": effort,
        "learning_loop": learning,
        "provenance_audit": provenance,
        "trend": trend,
    }

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    write_markdown_summary(report)

    sys.stderr.write(
        "OK: analytics report written to {0}\n".format(args.output)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

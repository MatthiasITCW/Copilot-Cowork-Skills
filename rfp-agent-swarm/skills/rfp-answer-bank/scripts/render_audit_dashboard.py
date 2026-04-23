#!/usr/bin/env python3
"""
render_audit_dashboard.py — produce an Adaptive Cards payload from the
shared RFP audit log.

Owner: rfp-answer-bank (shared infrastructure).

Input:
  --audit-json <path>   Path to a JSON export of audit-log.xlsx, produced
                        by the Excel built-in. Format: a JSON array of row
                        objects keyed by the canonical column schema.

Output (stdout):
  A single JSON object shaped for the Adaptive Cards built-in with:
    - kpi_row: total_events, ai_count, human_count, last_update_utc
    - timeline: events grouped by hour bucket (count per bucket)
    - event_type_distribution: donut slices (label + count)
    - actor_distribution: donut slices (ai/human + count)
    - event_stream: table of the most recent 25 events

Stdlib only.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict


def load_rows(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("render_audit_dashboard: expected a JSON array", file=sys.stderr)
        sys.exit(2)
    return data


def compute_kpis(rows):
    total = len(rows)
    actors = Counter(r.get("actor", "") for r in rows)
    last_update = ""
    if rows:
        stamps = [r.get("timestamp_utc", "") for r in rows if r.get("timestamp_utc")]
        if stamps:
            last_update = max(stamps)
    return {
        "total_events": total,
        "ai_count": actors.get("ai", 0),
        "human_count": actors.get("human", 0),
        "last_update_utc": last_update,
    }


def compute_timeline(rows):
    # Bucket by hour: 2026-04-22T10
    buckets = Counter()
    for r in rows:
        ts = r.get("timestamp_utc", "")
        if len(ts) >= 13:
            buckets[ts[:13]] += 1
    return [
        {"bucket_utc_hour": b + ":00Z", "count": c}
        for b, c in sorted(buckets.items())
    ]


def compute_event_type_distribution(rows):
    c = Counter(r.get("event_type", "") for r in rows if r.get("event_type"))
    return [{"label": k, "count": v} for k, v in c.most_common()]


def compute_actor_distribution(rows):
    c = Counter(r.get("actor", "") for r in rows if r.get("actor"))
    return [{"label": k, "count": v} for k, v in c.most_common()]


def compute_event_stream(rows, limit=25):
    sorted_rows = sorted(
        rows,
        key=lambda r: r.get("timestamp_utc", ""),
        reverse=True,
    )
    stream = []
    for r in sorted_rows[:limit]:
        stream.append({
            "timestamp_utc": r.get("timestamp_utc", ""),
            "skill": r.get("skill", ""),
            "event_type": r.get("event_type", ""),
            "actor": r.get("actor", ""),
            "target_type": r.get("target_type", ""),
            "target_id": r.get("target_id", ""),
            "reason": r.get("reason", ""),
        })
    return stream


def build_payload(rows, rfp_id):
    return {
        "card_type": "rfp_audit_dashboard",
        "rfp_id": rfp_id,
        "kpi_row": compute_kpis(rows),
        "timeline": compute_timeline(rows),
        "event_type_distribution": compute_event_type_distribution(rows),
        "actor_distribution": compute_actor_distribution(rows),
        "event_stream": compute_event_stream(rows),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audit-json", required=True,
                   help="Path to JSON export of audit-log.xlsx")
    p.add_argument("--rfp-id", required=True)
    args = p.parse_args()

    rows = load_rows(args.audit_json)
    # Filter to the requested RFP (defensive: export may contain more)
    rows = [r for r in rows if r.get("rfp_id") == args.rfp_id] or rows

    payload = build_payload(rows, args.rfp_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

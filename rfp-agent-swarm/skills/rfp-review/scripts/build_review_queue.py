#!/usr/bin/env python3
"""build_review_queue.py

Build an ordered review queue from drafter responses and gate verdicts.

Applies the prioritisation rules defined in references/flagging-rules.md:

  Rank 1: gate verdict = FAIL
  Rank 2: LOW confidence OR source = GENERATED
  Rank 3: MEDIUM with delta-from-source > threshold
  Rank 4: mandatory question with no response
  Rank 5: sensitive category (Security / Legal / Pricing / Compliance)
  Rank 6: gate verdict = WARN

Responses that pass the skip matrix are NOT added to the queue; instead they are
tagged review_status = "auto-approved" in a side-car output so that rfp-assemble
can enforce that every response has a disposition.

Python stdlib only. CLI:

  python build_review_queue.py \
      --responses working/responses.json \
      --gate-results working/gate_verdict.json \
      --output working/review_queue.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SENSITIVE_CATEGORIES = {"Security", "Legal", "Pricing", "Compliance"}
DEFAULT_DELTA_THRESHOLD = 0.35
DEFAULT_FRESHNESS_MAX_DAYS = 90


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _gate_verdict_for(question_id: str, gate_results: dict) -> str:
    """Return 'FAIL', 'WARN', or 'PASS' for a given question id."""
    items = gate_results.get("items", [])
    for item in items:
        if item.get("question_id") == question_id:
            return item.get("verdict", "PASS").upper()
    return "PASS"


def _gate_reasons_for(question_id: str, gate_results: dict) -> list[str]:
    for item in gate_results.get("items", []):
        if item.get("question_id") == question_id:
            return list(item.get("reasons", []))
    return []


def _classify(
    response: dict,
    gate_results: dict,
    delta_threshold: float,
    freshness_max_days: int,
) -> tuple[int | None, list[str]]:
    """Return (priority_rank, flag_reasons). priority_rank=None => auto-approve."""
    qid = response.get("question_id")
    confidence = (response.get("confidence") or "").upper()
    source = (response.get("source") or "").upper()
    category = response.get("category") or ""
    mandatory = bool(response.get("mandatory"))
    delta = float(response.get("delta_from_source") or 0.0)
    freshness = response.get("bank_freshness_days")
    answer = (response.get("answer") or "").strip()

    verdict = _gate_verdict_for(qid, gate_results)
    flags: list[str] = []

    if verdict == "FAIL":
        flags.append("gate_fail")
        flags.extend(f"gate:{r}" for r in _gate_reasons_for(qid, gate_results))
        return 1, flags

    if confidence == "LOW":
        flags.append("low_confidence")
        return 2, flags

    if source == "GENERATED":
        flags.append("generated_content")
        return 2, flags

    if confidence == "MEDIUM" and delta > delta_threshold:
        flags.append(f"high_delta:{delta:.2f}")
        return 3, flags

    if mandatory and not answer:
        flags.append("mandatory_unanswered")
        return 4, flags

    if category in SENSITIVE_CATEGORIES:
        flags.append(f"sensitive_category:{category}")
        return 5, flags

    if verdict == "WARN":
        flags.append("gate_warn")
        flags.extend(f"gate:{r}" for r in _gate_reasons_for(qid, gate_results))
        return 6, flags

    # Skip-matrix check — everything else must pass to auto-approve.
    if confidence != "HIGH":
        flags.append("non_high_confidence")
        return 5, flags
    if source != "KB":
        flags.append("non_kb_source")
        return 5, flags
    if freshness is None or freshness > freshness_max_days:
        flags.append("stale_or_unknown_freshness")
        return 5, flags

    return None, []


def _suggested_reviewer(category: str, roster: dict) -> str | None:
    if not roster:
        return None
    return roster.get(category) or roster.get("_default")


def build(
    responses: list[dict],
    gate_results: dict,
    roster: dict,
    delta_threshold: float,
    freshness_max_days: int,
) -> tuple[list[dict], list[dict]]:
    queue: list[dict] = []
    auto_approved: list[dict] = []

    for resp in responses:
        rank, flags = _classify(resp, gate_results, delta_threshold, freshness_max_days)
        if rank is None:
            auto_approved.append(
                {
                    "question_id": resp.get("question_id"),
                    "review_status": "auto-approved",
                }
            )
            continue

        queue.append(
            {
                "question_id": resp.get("question_id"),
                "tier": resp.get("confidence"),
                "category": resp.get("category"),
                "mandatory": bool(resp.get("mandatory")),
                "flag_reasons": flags,
                "priority_rank": rank,
                "suggested_reviewer": _suggested_reviewer(
                    resp.get("category") or "", roster
                ),
            }
        )

    # Sort: priority first, then category (so reviewers stay in context), then qid.
    queue.sort(
        key=lambda q: (
            q["priority_rank"],
            q.get("category") or "",
            q.get("question_id") or "",
        )
    )
    return queue, auto_approved


def _summarise(queue: list[dict]) -> dict:
    per_priority = Counter(q["priority_rank"] for q in queue)
    per_reviewer: dict[str, int] = defaultdict(int)
    for q in queue:
        per_reviewer[q.get("suggested_reviewer") or "_unassigned"] += 1
    return {
        "total_in_queue": len(queue),
        "per_priority": dict(sorted(per_priority.items())),
        "per_reviewer": dict(per_reviewer),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--responses", required=True, type=Path)
    parser.add_argument("--gate-results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--roster", type=Path, default=None,
                        help="Optional JSON map of category -> reviewer email.")
    parser.add_argument("--delta-threshold", type=float,
                        default=DEFAULT_DELTA_THRESHOLD)
    parser.add_argument("--freshness-max-days", type=int,
                        default=DEFAULT_FRESHNESS_MAX_DAYS)
    parser.add_argument("--filter-category", default=None,
                        help="If set, only include this category in the queue.")
    args = parser.parse_args(argv)

    try:
        responses_doc = _load_json(args.responses)
        gate_results = _load_json(args.gate_results)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: failed to load inputs: {exc}", file=sys.stderr)
        return 2

    responses = responses_doc.get("responses") if isinstance(responses_doc, dict) else responses_doc
    if not isinstance(responses, list):
        print("error: --responses must contain a list (top-level or under 'responses').",
              file=sys.stderr)
        return 2

    roster: dict = {}
    if args.roster:
        try:
            roster = _load_json(args.roster)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: could not load roster: {exc}", file=sys.stderr)

    queue, auto_approved = build(
        responses,
        gate_results if isinstance(gate_results, dict) else {"items": gate_results},
        roster,
        args.delta_threshold,
        args.freshness_max_days,
    )

    if args.filter_category:
        queue = [q for q in queue if q.get("category") == args.filter_category]

    summary = _summarise(queue)

    out = {
        "queue": queue,
        "auto_approved": auto_approved,
        "summary": summary,
        "config": {
            "delta_threshold": args.delta_threshold,
            "freshness_max_days": args.freshness_max_days,
            "filter_category": args.filter_category,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"wrote {len(queue)} queued items and {len(auto_approved)} auto-approved to {args.output}",
          file=sys.stderr)
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

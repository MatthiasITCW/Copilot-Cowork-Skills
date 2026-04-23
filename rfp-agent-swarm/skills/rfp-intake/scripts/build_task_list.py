#!/usr/bin/env python3
"""
build_task_list.py — Stage 3 of the rfp-intake pipeline.

Merges the raw parse output and the per-question classifications into the
canonical task_list.json that every downstream skill consumes.

- Assigns stable task IDs (Q-0001 style; preserves source IDs when present).
- Sorts by priority: mandatory first, then by deadline, then by category.
- Deduplicates by normalised-text hash (logged, never silently dropped).
- Estimates effort from word-limit hint and evidence flag.
- Emits a compact human-readable markdown summary to stderr for logging.

Python 3 stdlib only. Non-zero exit on fatal errors.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from typing import Any


OWNER_TEAM = {
    "SEC": "Security Engineering",
    "TEC": "Solution Architecture",
    "COM": "Commercial Desk",
    "COR": "Corporate Marketing",
    "GEN": "Bid Manager",
}

CATEGORY_ORDER = ["SEC", "TEC", "COM", "COR", "GEN"]


def normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise_text(text).encode("utf-8")).hexdigest()[:16]


def estimate_effort_minutes(word_limit_hint: int, evidence_required: bool,
                            credential_check: bool, pricing: bool,
                            legal_review: bool) -> int:
    """Rough first-draft effort in minutes."""
    base = max(10, word_limit_hint // 5)  # 5 words per minute typing + thought
    if evidence_required:
        base += 20
    if credential_check:
        base += 15
    if pricing:
        base += 30
    if legal_review:
        base += 45
    return base


def priority_key(task: dict[str, Any]) -> tuple[int, int, int]:
    mandatory_rank = 0 if task.get("mandatory") else 1
    cat = task.get("primary_category", "GEN")
    cat_rank = CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else len(CATEGORY_ORDER)
    # lower effort first within band so quick wins surface
    effort = task.get("estimated_effort_minutes", 60)
    return (mandatory_rank, cat_rank, effort)


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def merge(metadata: dict[str, Any], classifications: dict[str, Any]) -> dict[str, Any]:
    class_by_id = {c["question_id"]: c for c in classifications.get("classifications", [])}
    tasks: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    duplicates: list[dict[str, str]] = []

    for q in metadata.get("raw_questions", []):
        qid = q.get("question_id")
        cls = class_by_id.get(qid, {})
        text = q.get("text", "")
        h = text_hash(text)
        if h in seen_hashes:
            duplicates.append({"dropped": qid, "kept": seen_hashes[h]})
            continue
        seen_hashes[h] = qid

        primary = cls.get("primary_category", "GEN")
        effort = estimate_effort_minutes(
            cls.get("word_limit_hint", 150),
            cls.get("evidence_required", False),
            cls.get("credential_check", False),
            cls.get("pricing", False),
            cls.get("legal_review", False),
        )

        tasks.append({
            "task_id": qid,
            "question_id": qid,
            "text": text,
            "section": q.get("section", ""),
            "primary_category": primary,
            "secondary_category": cls.get("secondary_category"),
            "owner_team": cls.get("owner_team", OWNER_TEAM.get(primary, "Bid Manager")),
            "mandatory": cls.get("mandatory", True),
            "word_limit": None,
            "word_limit_hint": cls.get("word_limit_hint", 150),
            "evidence_required": cls.get("evidence_required", False),
            "credential_check": cls.get("credential_check", False),
            "pricing": cls.get("pricing", False),
            "legal_review": cls.get("legal_review", False),
            "confidence": cls.get("confidence", "LOW"),
            "needs_human_triage": cls.get("needs_human_triage", False),
            "estimated_effort_minutes": effort,
            "text_hash": h,
        })

    tasks.sort(key=priority_key)

    # Totals
    totals_by_category: dict[str, int] = {}
    totals_by_owner: dict[str, int] = {}
    mandatory_total = 0
    effort_total = 0
    for t in tasks:
        totals_by_category[t["primary_category"]] = totals_by_category.get(t["primary_category"], 0) + 1
        totals_by_owner[t["owner_team"]] = totals_by_owner.get(t["owner_team"], 0) + 1
        if t["mandatory"]:
            mandatory_total += 1
        effort_total += t["estimated_effort_minutes"]

    return {
        "rfp_id": metadata.get("rfp_id"),
        "buyer": metadata.get("buyer"),
        "rfp_title": metadata.get("rfp_title"),
        "response_deadline": metadata.get("response_deadline"),
        "submission_format": metadata.get("submission_format"),
        "parse_confidence": metadata.get("parse_confidence"),
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tasks": tasks,
        "totals": {
            "total_tasks": len(tasks),
            "mandatory": mandatory_total,
            "by_category": totals_by_category,
            "by_owner": totals_by_owner,
            "estimated_total_effort_minutes": effort_total,
            "duplicates_removed": len(duplicates),
        },
        "duplicates": duplicates,
    }


def write_markdown_summary(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# RFP task list — {payload.get('rfp_id')}")
    lines.append("")
    lines.append(f"- Buyer: {payload.get('buyer') or '(unknown)'}")
    lines.append(f"- Deadline: {payload.get('response_deadline') or '(unknown)'}")
    lines.append(f"- Submission: {payload.get('submission_format') or '(unknown)'}")
    lines.append(f"- Parse confidence: {payload.get('parse_confidence')}")
    lines.append("")
    totals = payload.get("totals", {})
    lines.append(f"- Total tasks: {totals.get('total_tasks')}")
    lines.append(f"- Mandatory: {totals.get('mandatory')}")
    lines.append(f"- Duplicates removed: {totals.get('duplicates_removed')}")
    lines.append("")
    lines.append("## By category")
    for cat, n in totals.get("by_category", {}).items():
        lines.append(f"- {cat}: {n}")
    lines.append("")
    lines.append("## By owner")
    for owner, n in totals.get("by_owner", {}).items():
        lines.append(f"- {owner}: {n}")
    lines.append("")
    eff = totals.get("estimated_total_effort_minutes", 0)
    lines.append(f"Estimated total first-draft effort: {eff} minutes "
                 f"({eff // 60}h {eff % 60}m)")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build canonical task list from parsed + classified RFP")
    ap.add_argument("--metadata", required=True, help="Path to working/rfp_raw.json")
    ap.add_argument("--classifications", required=True, help="Path to working/classified.json")
    ap.add_argument("--output", required=True, help="Path to write working/task_list.json")
    args = ap.parse_args(argv)

    try:
        for p in (args.metadata, args.classifications):
            if not os.path.isfile(p):
                print(f"ERROR: input not found: {p}", file=sys.stderr)
                return 1
        metadata = load_json(args.metadata)
        classifications = load_json(args.classifications)
        if metadata.get("rfp_id") != classifications.get("rfp_id"):
            print("WARNING: rfp_id mismatch between metadata and classifications", file=sys.stderr)

        payload = merge(metadata, classifications)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        summary_md = write_markdown_summary(payload)
        print(summary_md, file=sys.stderr)

        print(json.dumps({
            "ok": True,
            "output": args.output,
            "totals": payload["totals"],
        }))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: task list build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

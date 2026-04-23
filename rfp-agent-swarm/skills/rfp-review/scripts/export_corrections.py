#!/usr/bin/env python3
"""export_corrections.py

Roll up working/corrections.jsonl into a consolidated JSON payload for
consumption by rfp-answer-bank.merge_corrections. Optionally filter by date.

The output groups corrections by reason, by category, and by question pattern
(where "question pattern" is a normalised hash of the question id prefix, used
by the answer bank to cluster similar questions).

A human-readable summary is also emitted to stderr in markdown, so reviewers
can eyeball the batch before it feeds the learning loop.

Python stdlib only. CLI:

  python export_corrections.py \
      --input working/corrections.jsonl \
      --output working/corrections_export.json \
      --since 2026-01-01
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VALID_REASONS = {
    "FACTUAL_ERROR",
    "OUTDATED_SOURCE",
    "TONE_OR_STYLE",
    "MISSING_CONTEXT",
    "CATEGORY_MISCLASSIFICATION",
    "UNANSWERABLE_FROM_KB",
    "POLICY_UPDATE",
    "COMPLIANCE_NUANCE",
}

REASON_TO_KB_ACTION = {
    "FACTUAL_ERROR": "replace",
    "OUTDATED_SOURCE": "replace",
    "TONE_OR_STYLE": "no-op",
    "MISSING_CONTEXT": "add-sibling",
    "CATEGORY_MISCLASSIFICATION": "reclassify",
    "UNANSWERABLE_FROM_KB": "add-new",
    "POLICY_UPDATE": "retire+add-new",
    "COMPLIANCE_NUANCE": "add-sibling",
}


def _parse_since(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    try:
        d = _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"error: --since must be YYYY-MM-DD ({exc}).") from exc
    return _dt.datetime.combine(d, _dt.time.min, tzinfo=_dt.timezone.utc)


def _parse_timestamp(value: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _question_pattern(qid: str) -> str:
    """Normalise a question id to a cluster key.
    Convention: Q-0142 -> Q-01xx, Q-2045 -> Q-20xx. Falls back to qid if no digits."""
    if not qid:
        return "_unknown"
    digits = "".join(ch for ch in qid if ch.isdigit())
    if len(digits) < 2:
        return qid
    prefix = qid.split(digits[-2:])[0] if digits[-2:] in qid else qid[: -2]
    return f"{prefix}{digits[:-2]}xx"


def _load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                print(
                    f"error: malformed JSONL at {path}:{lineno}: {exc}",
                    file=sys.stderr,
                )
                raise SystemExit(2) from exc
    return records


def _supersede_filter(records: list[dict]) -> list[dict]:
    """Drop records that have been superseded by a later one."""
    superseded = {r.get("supersedes") for r in records if r.get("supersedes")}
    return [r for r in records if r.get("correction_id") not in superseded]


def _rollup(records: list[dict]) -> dict[str, Any]:
    by_reason: dict[str, list[dict]] = defaultdict(list)
    by_category: dict[str, list[dict]] = defaultdict(list)
    by_pattern: dict[str, list[dict]] = defaultdict(list)

    for r in records:
        reason = r.get("reason")
        if reason not in VALID_REASONS:
            continue
        by_reason[reason].append(r)
        by_category[r.get("category") or "_uncategorised"].append(r)
        by_pattern[_question_pattern(r.get("question_id") or "")].append(r)

    payload = {
        "total": len(records),
        "by_reason": {
            reason: {
                "count": len(items),
                "kb_action": REASON_TO_KB_ACTION.get(reason, "unknown"),
                "records": items,
            }
            for reason, items in by_reason.items()
        },
        "by_category": {
            cat: {"count": len(items), "reasons": dict(Counter(r["reason"] for r in items))}
            for cat, items in by_category.items()
        },
        "by_question_pattern": {
            pat: {"count": len(items), "question_ids": sorted({r.get("question_id") for r in items if r.get("question_id")})}
            for pat, items in by_pattern.items()
        },
    }
    return payload


def _markdown_summary(payload: dict[str, Any], since: _dt.datetime | None) -> str:
    lines = []
    lines.append("# Correction Export Summary")
    if since:
        lines.append(f"Since: {since.date().isoformat()}")
    lines.append(f"Total corrections: {payload['total']}")
    lines.append("")
    lines.append("## By reason")
    lines.append("| Reason | Count | KB action |")
    lines.append("|--------|-------|-----------|")
    for reason, info in sorted(payload["by_reason"].items()):
        lines.append(f"| {reason} | {info['count']} | {info['kb_action']} |")
    lines.append("")
    lines.append("## By category")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for cat, info in sorted(payload["by_category"].items()):
        lines.append(f"| {cat} | {info['count']} |")
    lines.append("")
    lines.append("## By question pattern")
    lines.append("| Pattern | Count |")
    lines.append("|---------|-------|")
    for pat, info in sorted(payload["by_question_pattern"].items()):
        lines.append(f"| {pat} | {info['count']} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--since", default=None,
                        help="YYYY-MM-DD; only include corrections on or after this date.")
    parser.add_argument("--include-tone-style", action="store_true",
                        help="Include TONE_OR_STYLE records in the export (default: exclude).")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    records = _load_jsonl(args.input)
    since = _parse_since(args.since)

    if since is not None:
        filtered = []
        for r in records:
            ts = _parse_timestamp(r.get("timestamp") or "")
            if ts is None:
                continue
            if ts >= since:
                filtered.append(r)
        records = filtered

    records = _supersede_filter(records)

    if not args.include_tone_style:
        records = [r for r in records if r.get("reason") != "TONE_OR_STYLE"]

    payload = _rollup(records)
    payload["generated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    payload["filters"] = {
        "since": args.since,
        "include_tone_style": args.include_tone_style,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(_markdown_summary(payload, since), file=sys.stderr)
    print(f"\nwrote export to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

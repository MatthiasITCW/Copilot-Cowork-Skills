#!/usr/bin/env python3
"""log_correction.py

Append a single reviewer correction to working/corrections.jsonl.

The correction record is the atom of the learning loop. Each record carries:

  - question_id
  - original response (inline or resolved from a responses.json file)
  - corrected response (inline or read from a file)
  - reason (from the fixed taxonomy; unknown values are rejected)
  - reviewer email
  - timestamp (UTC, ISO-8601)
  - category (optional, denormalised for rollup)
  - confidence delta, if tier scores are available on both sides
  - corrected_hash (sha256 of corrected text) for idempotency
  - correction_id (deterministic, for supersession)

Idempotency: if a record with the same (question_id, reviewer, corrected_hash)
already exists in the target file, this script logs a no-op and exits 0.

Auto-escalation: if --reason TONE_OR_STYLE is chosen but the corrected text
differs from the original by more than --tone-char-cap chars (default 120),
the record is re-classified to FACTUAL_ERROR and a warning is printed. The
caller can pass --confirm-tone to suppress the reclassification.

Python stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
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

TIER_SCORES = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.9, "GOLD": 1.0}
DEFAULT_TONE_CHAR_CAP = 120


def _resolve_text(value: str, question_id: str) -> str:
    """If value is a path to a JSON file, pull the response for question_id.
    Otherwise return value unchanged (treated as inline text)."""
    p = Path(value)
    if p.exists() and p.is_file() and p.suffix.lower() == ".json":
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: {p} is not valid JSON: {exc}") from exc
        responses = doc.get("responses") if isinstance(doc, dict) else doc
        if not isinstance(responses, list):
            raise SystemExit(f"error: {p} does not contain a responses list.")
        for r in responses:
            if r.get("question_id") == question_id:
                return r.get("answer") or ""
        raise SystemExit(
            f"error: question_id {question_id!r} not found in {p}"
        )
    return value


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _correction_id(question_id: str, reviewer: str, corrected_hash: str) -> str:
    seed = f"{question_id}|{reviewer}|{corrected_hash}".encode("utf-8")
    return "corr_" + hashlib.sha1(seed).hexdigest()[:16]


def _confidence_delta(original_tier: str | None, corrected_tier: str | None) -> float | None:
    if not original_tier or not corrected_tier:
        return None
    a = TIER_SCORES.get(original_tier.upper())
    b = TIER_SCORES.get(corrected_tier.upper())
    if a is None or b is None:
        return None
    return round(b - a, 3)


def _already_logged(path: Path, correction_id: str) -> bool:
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("correction_id") == correction_id:
                return True
    return False


def _maybe_escalate(
    reason: str,
    original_text: str,
    corrected_text: str,
    cap: int,
    confirm_tone: bool,
) -> tuple[str, bool]:
    """Returns (final_reason, was_reclassified)."""
    if reason != "TONE_OR_STYLE":
        return reason, False
    delta_chars = abs(len(corrected_text) - len(original_text))
    if delta_chars <= cap:
        return reason, False
    if confirm_tone:
        print(
            f"warning: tone edit is {delta_chars} chars (> {cap}); "
            "reviewer explicitly confirmed via --confirm-tone.",
            file=sys.stderr,
        )
        return reason, False
    print(
        f"warning: TONE_OR_STYLE edit exceeded {cap} chars "
        f"({delta_chars}); auto-reclassifying to FACTUAL_ERROR. "
        "Pass --confirm-tone to keep TONE_OR_STYLE.",
        file=sys.stderr,
    )
    return "FACTUAL_ERROR", True


def build_record(args: argparse.Namespace) -> dict[str, Any]:
    original_text = _resolve_text(args.original, args.question_id)
    corrected_text = _resolve_text(args.corrected, args.question_id)

    if args.reason not in VALID_REASONS:
        raise SystemExit(
            f"error: UnknownReason {args.reason!r}. "
            f"Expected one of: {', '.join(sorted(VALID_REASONS))}."
        )

    final_reason, reclassified = _maybe_escalate(
        args.reason,
        original_text,
        corrected_text,
        args.tone_char_cap,
        args.confirm_tone,
    )

    corrected_hash = _hash(corrected_text)
    cid = _correction_id(args.question_id, args.reviewer, corrected_hash)

    record: dict[str, Any] = {
        "correction_id": cid,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "question_id": args.question_id,
        "category": args.category,
        "reviewer": args.reviewer,
        "reason": final_reason,
        "reason_was_auto_reclassified": reclassified,
        "original_text": original_text,
        "corrected_text": corrected_text,
        "corrected_hash": corrected_hash,
        "confidence_delta": _confidence_delta(args.original_tier, args.corrected_tier),
        "supersedes": args.supersedes,
        "tags": args.tag,
    }
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--question-id", required=True)
    parser.add_argument("--original", required=True,
                        help="Inline text OR path to a responses.json file.")
    parser.add_argument("--corrected", required=True,
                        help="Inline text OR path to a responses.json file.")
    parser.add_argument("--reason", required=True,
                        help=f"One of: {', '.join(sorted(VALID_REASONS))}")
    parser.add_argument("--reviewer", required=True,
                        help="Reviewer email.")
    parser.add_argument("--appendto", required=True, type=Path,
                        help="Target JSONL file (will be created if missing).")
    parser.add_argument("--category", default=None)
    parser.add_argument("--original-tier", default=None,
                        help="LOW/MEDIUM/HIGH/GOLD — optional.")
    parser.add_argument("--corrected-tier", default=None)
    parser.add_argument("--supersedes", default=None,
                        help="Prior correction_id this record replaces.")
    parser.add_argument("--tag", action="append", default=[],
                        help="Optional free-form tag; may repeat.")
    parser.add_argument("--tone-char-cap", type=int, default=DEFAULT_TONE_CHAR_CAP)
    parser.add_argument("--confirm-tone", action="store_true",
                        help="Suppress auto-reclassification of TONE_OR_STYLE.")
    args = parser.parse_args(argv)

    record = build_record(args)

    if _already_logged(args.appendto, record["correction_id"]):
        print(
            f"no-op: correction {record['correction_id']} already present in "
            f"{args.appendto}",
            file=sys.stderr,
        )
        return 0

    args.appendto.parent.mkdir(parents=True, exist_ok=True)
    with args.appendto.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(
        f"logged correction {record['correction_id']} "
        f"(reason={record['reason']}) to {args.appendto}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

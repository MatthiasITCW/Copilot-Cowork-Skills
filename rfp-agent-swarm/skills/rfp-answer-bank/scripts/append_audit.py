#!/usr/bin/env python3
"""
append_audit.py — emit a canonical audit row for the shared RFP audit log.

Owner: rfp-answer-bank (shared infrastructure).
Callers: every rfp-* sibling skill.

Behavior:
- Validates event_type against the canonical catalogue.
- Auto-generates event_id (UUID4 hex) and timestamp_utc (ISO 8601 Zulu).
- Rejects delete operations (no such thing in the audit log).
- Validates before/after as JSON when provided.
- Emits a single JSON object on stdout; the Excel built-in appends it to
  output/rfp-<rfp_id>/audit-log.xlsx on sheet "AuditLog".

Exit codes:
  0 — row emitted.
  2 — schema / validation failure.
  3 — delete attempt.

Stdlib only.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

EVENT_TYPE_CATALOGUE = {
    "rfp-intake": {
        "RFP_INTAKE_STARTED", "QUESTION_EXTRACTED", "CLASSIFICATION_APPLIED",
        "TASK_LIST_CREATED", "INTAKE_COMPLETE",
    },
    "rfp-fit-assessment": {
        "FIT_ASSESSMENT_STARTED", "SCORECARD_COMPUTED",
        "GO_NO_GO_RECOMMENDED", "HUMAN_DECISION_LOGGED",
    },
    "rfp-respond": {
        "RESPONSE_DRAFT_STARTED", "KB_MATCH_FOUND", "RESPONSE_GENERATED",
        "TEAM_ROUTED", "RESPONSE_BATCH_COMPLETE",
    },
    "rfp-gates": {
        "GATE_REQUESTED", "GATE_APPROVED", "GATE_REJECTED",
        "PIPELINE_PAUSED", "PIPELINE_RESUMED",
    },
    "rfp-review": {
        "REVIEW_QUEUE_BUILT", "CORRECTION_CAPTURED",
        "CORRECTION_REASON_TAGGED", "REVIEW_COMPLETE",
    },
    "rfp-assemble": {
        "ASSEMBLY_STARTED", "FORMAT_SELECTED", "DELIVERABLE_GENERATED",
        "ANALYTICS_COMPUTED", "RECORD_SET_PACKAGED",
    },
    "rfp-answer-bank": {
        "BANK_SEARCHED", "KB_ENTRY_ADDED", "KB_ENTRY_UPDATED",
        "LOOPIO_SYNC_COMPLETED", "CORRECTIONS_MERGED",
    },
}

VALID_ACTORS = {"ai", "human"}
VALID_TARGET_TYPES = {"question", "gate", "correction", "deliverable", "kb_entry"}
DELETE_MARKERS = {"DELETE", "HARD_DELETE", "REMOVE", "PURGE"}


def fail(msg, code=2):
    print(f"append_audit: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_json_field(raw, field_name):
    if raw is None or raw == "":
        return None
    try:
        json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"--{field_name} is not valid JSON: {e}")
    return raw


def validate(args):
    if args.skill not in EVENT_TYPE_CATALOGUE:
        fail(f"unknown skill '{args.skill}'. Must be one of {sorted(EVENT_TYPE_CATALOGUE)}")

    allowed = EVENT_TYPE_CATALOGUE[args.skill]
    if args.event_type not in allowed:
        fail(f"event_type '{args.event_type}' not valid for skill '{args.skill}'. "
             f"Allowed: {sorted(allowed)}")

    if args.event_type.upper() in DELETE_MARKERS or "DELETE" in args.event_type.upper():
        fail(f"delete operations are forbidden in the audit log: {args.event_type}", code=3)

    if args.actor not in VALID_ACTORS:
        fail(f"actor must be one of {sorted(VALID_ACTORS)}")

    if args.target_type not in VALID_TARGET_TYPES:
        fail(f"target_type must be one of {sorted(VALID_TARGET_TYPES)}")

    if args.confidence is not None:
        if not (0.0 <= args.confidence <= 1.0):
            fail("confidence must be in [0.0, 1.0]")


def build_row(args):
    return {
        "event_id": uuid.uuid4().hex,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rfp_id": args.rfp_id,
        "skill": args.skill,
        "event_type": args.event_type,
        "actor": args.actor,
        "actor_id": args.actor_id,
        "target_type": args.target_type,
        "target_id": args.target_id,
        "before": parse_json_field(args.before, "before"),
        "after": parse_json_field(args.after, "after"),
        "reason": args.reason or "",
        "provenance_id": args.provenance_id or "",
        "confidence": args.confidence if args.confidence is not None else "",
        "notes": args.notes or "",
    }


def main():
    p = argparse.ArgumentParser(description="Emit a canonical audit row.")
    p.add_argument("--rfp-id", required=True)
    p.add_argument("--skill", required=True)
    p.add_argument("--event-type", required=True)
    p.add_argument("--actor", required=True, choices=sorted(VALID_ACTORS))
    p.add_argument("--actor-id", required=True)
    p.add_argument("--target-type", required=True, choices=sorted(VALID_TARGET_TYPES))
    p.add_argument("--target-id", required=True)
    p.add_argument("--before", default=None)
    p.add_argument("--after", default=None)
    p.add_argument("--reason", default=None)
    p.add_argument("--provenance-id", default=None)
    p.add_argument("--confidence", type=float, default=None)
    p.add_argument("--notes", default=None)
    p.add_argument("--output-dir", required=True,
                   help="output/rfp-<id>/ — used only to confirm path convention")
    args = p.parse_args()

    expected_suffix = f"rfp-{args.rfp_id}"
    if expected_suffix not in args.output_dir.rstrip("/"):
        print(f"append_audit: warning — output-dir '{args.output_dir}' does not contain "
              f"'{expected_suffix}'", file=sys.stderr)

    validate(args)
    row = build_row(args)
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

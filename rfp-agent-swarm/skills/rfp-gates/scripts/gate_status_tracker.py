#!/usr/bin/env python3
"""
gate_status_tracker.py — rfp-gates Step 4 status aggregator.

Reads the status-of-record (`gate_statuses.json`, populated by the Power
Automate flow that handles approver responses) and aggregates the three gates
into a single verdict.

Verdict semantics:
    PASS    — all three gates Approved with valid signatures
    FAIL    — at least one gate Rejected
    PENDING — neither PASS nor FAIL yet (at least one gate still awaiting
              response, and none Rejected)

There is no FORCE, no BYPASS, no OVERRIDE. Deadline pressure does not change
the verdict.

Usage:
    python scripts/gate_status_tracker.py \\
        --statuses working/gate_statuses.json \\
        --output working/gate_verdict.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GATES = ("security", "legal", "pricing")

REQUIRED_SIGNATURE_FIELDS = ("approver_email", "approver_role", "decision", "decided_at_utc")


@dataclass
class GateStatus:
    gate: str
    status: str  # Pending / Approved / Rejected / Invalid
    approver_email: str = ""
    approver_role: str = ""
    decided_at_utc: str = ""
    requested_at_utc: str = ""
    time_in_gate_seconds: float | None = None
    reason: str = ""
    reason_code: str = ""
    affected_questions: list[str] = None  # type: ignore


def _parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _validate_signature(entry: dict) -> tuple[bool, str]:
    missing = [f for f in REQUIRED_SIGNATURE_FIELDS if not entry.get(f)]
    if missing:
        return False, f"Missing signature fields: {', '.join(missing)}"
    decision = (entry.get("decision") or "").lower()
    if decision not in ("approved", "rejected"):
        return False, f"Unknown decision value: {entry.get('decision')}"
    if decision == "rejected" and not (entry.get("reason") or entry.get("comment")):
        return False, "Rejection without reason."
    return True, ""


def compute_gate_status(gate: str, entry: dict | None) -> GateStatus:
    if not entry:
        return GateStatus(gate=gate, status="Pending", affected_questions=[])

    if "decision" not in entry:
        return GateStatus(
            gate=gate, status="Pending",
            requested_at_utc=entry.get("requested_at_utc", ""),
            affected_questions=[],
        )

    ok, err = _validate_signature(entry)
    if not ok:
        return GateStatus(
            gate=gate, status="Invalid",
            approver_email=entry.get("approver_email", ""),
            approver_role=entry.get("approver_role", ""),
            decided_at_utc=entry.get("decided_at_utc", ""),
            requested_at_utc=entry.get("requested_at_utc", ""),
            reason=err, reason_code="SIGNATURE_INVALID",
            affected_questions=[],
        )

    requested = _parse_iso(entry.get("requested_at_utc", ""))
    decided = _parse_iso(entry.get("decided_at_utc", ""))
    tig = None
    if requested and decided:
        tig = (decided - requested).total_seconds()

    decision = entry["decision"].capitalize()
    return GateStatus(
        gate=gate,
        status=decision,
        approver_email=entry.get("approver_email", ""),
        approver_role=entry.get("approver_role", ""),
        decided_at_utc=entry.get("decided_at_utc", ""),
        requested_at_utc=entry.get("requested_at_utc", ""),
        time_in_gate_seconds=tig,
        reason=entry.get("reason") or entry.get("comment") or "",
        reason_code=entry.get("reason_code") or "",
        affected_questions=entry.get("affected_questions") or [],
    )


def aggregate(statuses: list[GateStatus]) -> dict[str, Any]:
    by_gate = {s.gate: s for s in statuses}
    any_rejected = any(s.status == "Rejected" for s in statuses)
    any_invalid = any(s.status == "Invalid" for s in statuses)
    any_pending = any(s.status == "Pending" for s in statuses)
    all_approved = all(s.status == "Approved" for s in statuses) and len(statuses) == len(GATES)

    if any_invalid:
        verdict = "FAIL"
        next_action = "Invalidate the affected approvals and re-request."
    elif any_rejected:
        verdict = "FAIL"
        next_action = "Route rejection(s) per gate-rejection-routing.md; pipeline remains paused."
    elif all_approved:
        verdict = "PASS"
        next_action = "Proceed to rfp-assemble."
    elif any_pending:
        verdict = "PENDING"
        next_action = "Await approver responses; escalate per SLA if stalled."
    else:
        verdict = "PENDING"
        next_action = "Status incomplete; re-check inputs."

    return {
        "verdict": verdict,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "gates": {g: asdict(by_gate.get(g, GateStatus(gate=g, status="Pending", affected_questions=[]))) for g in GATES},
        "rejections": [
            {
                "gate": s.gate,
                "approver_email": s.approver_email,
                "reason": s.reason,
                "reason_code": s.reason_code,
                "affected_questions": s.affected_questions or [],
                "decided_at_utc": s.decided_at_utc,
            }
            for s in statuses if s.status == "Rejected"
        ],
        "sla": {
            s.gate: {
                "time_in_gate_seconds": s.time_in_gate_seconds,
                "over_sla": (
                    s.time_in_gate_seconds is not None
                    and s.time_in_gate_seconds > 16 * 3600
                ),
            }
            for s in statuses
        },
        "next_action": next_action,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="rfp-gates status aggregator")
    ap.add_argument("--statuses", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)

    path = Path(args.statuses)
    if not path.exists():
        # No statuses file yet -> all Pending
        raw = {}
    else:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

    gate_statuses = [compute_gate_status(g, raw.get(g)) for g in GATES]
    verdict = aggregate(gate_statuses)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2)

    print(f"Verdict: {verdict['verdict']} -> {verdict['next_action']}")
    # Exit 0 for PASS; 1 for PENDING; 2 for FAIL (useful in CI/workflow engines).
    return {"PASS": 0, "PENDING": 1, "FAIL": 2}[verdict["verdict"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

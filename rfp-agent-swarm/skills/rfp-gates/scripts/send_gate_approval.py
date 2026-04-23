#!/usr/bin/env python3
"""
send_gate_approval.py — rfp-gates Step 4 approval-card builder.

Builds the Teams adaptive-card payload for a single gate approval request
(Security Completeness, Legal Review, or Pricing Approval).

This script does NOT transmit the card. In production, a Power Automate flow
consumes the emitted payload and posts it to Teams. Locally, the payload is
rendered via the render-ui tool by the skill orchestrator.

Usage:
    python scripts/send_gate_approval.py \\
        --gate security \\
        --precheck working/gate_precheck.json \\
        --approver-email security.lead@example.com \\
        --approver-name "S. Lead" \\
        --rfp-id RFP-2026-001 \\
        --buyer-name "Acme Corp" \\
        --deadline 2026-05-01T17:00:00Z \\
        --evidence-pack-link "https://example.sharepoint.com/..." \\
        --output working/approval_request_security.json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GATE_LABELS = {
    "security": "Security Completeness Gate",
    "legal": "Legal Review Gate",
    "pricing": "Pricing Approval Gate",
}

GATE_ROLES = {
    "security": "Security Lead",
    "legal": "Legal Counsel",
    "pricing": "Account Executive",
}


def load_precheck(path: str) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def precheck_for(gate: str, precheck: dict) -> dict:
    key = f"{gate}_precheck"
    if key not in precheck:
        raise ValueError(f"Precheck JSON is missing '{key}'.")
    return precheck[key]


def build_risks_bullets(gate_precheck: dict) -> list[str]:
    """Condense precheck issues into human-readable risk bullets."""
    issues = gate_precheck.get("issues", [])
    bullets: list[str] = []
    by_code: dict[str, list[str]] = {}
    for it in issues:
        by_code.setdefault(it["code"], []).append(it.get("question_id", "?"))
    for code, qids in sorted(by_code.items()):
        sample = ", ".join(sorted(set(qids))[:5])
        more = "" if len(qids) <= 5 else f" (+{len(qids) - 5} more)"
        bullets.append(f"{code}: {sample}{more}")
    if not bullets:
        bullets.append("No automated issues detected. Human judgement items remain.")
    return bullets


def build_card_payload(
    gate: str,
    gate_precheck: dict,
    *,
    rfp_id: str,
    buyer_name: str,
    deadline: str,
    approver_email: str,
    approver_name: str,
    evidence_pack_link: str,
) -> dict[str, Any]:
    """Build an Adaptive Card v1.5 payload."""
    gate_label = GATE_LABELS[gate]
    role = GATE_ROLES[gate]
    risk_bullets = build_risks_bullets(gate_precheck)
    card_id = str(uuid.uuid4())

    facts = [
        {"title": "RFP ID", "value": rfp_id},
        {"title": "Buyer", "value": buyer_name},
        {"title": "Deadline (UTC)", "value": deadline},
        {"title": "Approver", "value": f"{approver_name} ({role})"},
        {"title": "Items in scope", "value": str(gate_precheck.get("total_items", 0))},
        {"title": "Items flagged", "value": str(gate_precheck.get("flagged_items", 0))},
        {"title": "Precheck ready_to_send", "value": str(gate_precheck.get("ready_to_send", False))},
    ]

    body = [
        {"type": "TextBlock", "size": "Large", "weight": "Bolder",
         "text": f"{gate_label} — Approval Required"},
        {"type": "TextBlock", "isSubtle": True,
         "text": f"Pipeline is paused. This gate cannot be bypassed."},
        {"type": "FactSet", "facts": facts},
        {"type": "TextBlock", "weight": "Bolder", "text": "Precheck findings"},
    ]
    for bullet in risk_bullets:
        body.append({"type": "TextBlock", "wrap": True, "text": f"- {bullet}"})

    body.append({
        "type": "TextBlock", "wrap": True,
        "text": f"[Open evidence pack]({evidence_pack_link})",
    })

    body.append({
        "type": "Input.Text", "id": "comment", "isMultiline": True,
        "placeholder": "Required if rejecting; optional if approving",
        "label": "Comment",
    })

    actions = [
        {"type": "Action.Submit", "title": "Approve",
         "data": {"verb": "approve", "gate": gate, "card_id": card_id}},
        {"type": "Action.Submit", "title": "Reject",
         "style": "destructive",
         "data": {"verb": "reject", "gate": gate, "card_id": card_id,
                  "comment_required": True}},
    ]

    card = {
        "type": "AdaptiveCard",
        "version": "1.5",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "body": body,
        "actions": actions,
        "metadata": {"webUrl": evidence_pack_link},
    }
    return card


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="rfp-gates approval-card builder")
    ap.add_argument("--gate", required=True, choices=["security", "legal", "pricing"])
    ap.add_argument("--precheck", required=True)
    ap.add_argument("--approver-email", required=True)
    ap.add_argument("--approver-name", default="")
    ap.add_argument("--rfp-id", default="RFP-UNKNOWN")
    ap.add_argument("--buyer-name", default="Buyer")
    ap.add_argument("--deadline", default="")
    ap.add_argument("--evidence-pack-link", default="")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)

    precheck = load_precheck(args.precheck)
    gate_pre = precheck_for(args.gate, precheck)

    if not gate_pre.get("ready_to_send", False):
        print(
            f"BLOCKED: {args.gate} precheck has hard-fail issues. "
            "Resolve them in the originating skill before requesting approval.",
            file=sys.stderr,
        )
        return 2

    card = build_card_payload(
        args.gate,
        gate_pre,
        rfp_id=args.rfp_id,
        buyer_name=args.buyer_name,
        deadline=args.deadline,
        approver_email=args.approver_email,
        approver_name=args.approver_name or args.approver_email,
        evidence_pack_link=args.evidence_pack_link,
    )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "card_payload": card,
        "metadata": {
            "gate": args.gate,
            "gate_label": GATE_LABELS[args.gate],
            "approver_email": args.approver_email,
            "approver_name": args.approver_name or args.approver_email,
            "approver_role": GATE_ROLES[args.gate],
            "rfp_id": args.rfp_id,
            "buyer_name": args.buyer_name,
            "deadline_utc": args.deadline,
            "response_version_hash": precheck.get("response_version_hash"),
            "transport": "power-automate-teams-adaptive-card",
            "backup_required_if_stalled_hours": 16,
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Built {args.gate} approval card for {args.approver_email}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

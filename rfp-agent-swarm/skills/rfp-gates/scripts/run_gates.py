#!/usr/bin/env python3
"""
run_gates.py — rfp-gates Step 4 precheck.

Produces the machine-checkable evidence pack for the three gates
(Security Completeness, Legal Review, Pricing Approval). This script does NOT
grant approval; it produces the pack that a human approver reviews.

Non-zero exit if any auto-fail condition is hit. The gate request must not be
dispatched while the precheck is failing.

Usage:
    python scripts/run_gates.py \\
        --responses working/responses.json \\
        --approved-certs working/approved_certs.json \\
        --approved-audits working/approved_audits.json \\
        --pricing-inputs working/authorised_pricing_inputs.json \\
        --review-flags working/review_flags.json \\
        --pricing-policy working/pricing_policy.json \\
        --output working/gate_precheck.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------- Auto-fail codes ----------

SEC_MISSING = "SEC_MISSING"
CERT_UNVERIFIED = "CERT_UNVERIFIED"
AUDIT_DATE_UNVERIFIED = "AUDIT_DATE_UNVERIFIED"
SEC_GENERATED_UNREVIEWED = "SEC_GENERATED_UNREVIEWED"
CRYPTO_UNAPPROVED = "CRYPTO_UNAPPROVED"

LEGAL_UNREVIEWED = "LEGAL_UNREVIEWED"
LEGAL_BLOCKER = "LEGAL_BLOCKER"
LEGAL_NONSTANDARD_MISSING = "LEGAL_NONSTANDARD_MISSING"

PRICING_GENERATED = "PRICING_GENERATED"
PRICING_UNLINKED = "PRICING_UNLINKED"
PRICING_INPUT_UNKNOWN = "PRICING_INPUT_UNKNOWN"
PRICING_VERSION_STALE = "PRICING_VERSION_STALE"
PRICING_DISCOUNT_UNAUTHORISED = "PRICING_DISCOUNT_UNAUTHORISED"
PRICING_BUNDLE_UNAUTHORISED = "PRICING_BUNDLE_UNAUTHORISED"
PRICING_EXPIRED = "PRICING_EXPIRED"

HARD_FAIL_CODES = {
    SEC_MISSING, CERT_UNVERIFIED, AUDIT_DATE_UNVERIFIED,
    SEC_GENERATED_UNREVIEWED, CRYPTO_UNAPPROVED,
    LEGAL_UNREVIEWED, LEGAL_BLOCKER, LEGAL_NONSTANDARD_MISSING,
    PRICING_GENERATED, PRICING_UNLINKED, PRICING_INPUT_UNKNOWN,
    PRICING_VERSION_STALE, PRICING_DISCOUNT_UNAUTHORISED,
    PRICING_BUNDLE_UNAUTHORISED, PRICING_EXPIRED,
}


@dataclass
class Issue:
    code: str
    gate: str
    question_id: str
    detail: str
    severity: str = "hard"


@dataclass
class GatePrecheck:
    gate: str
    total_items: int
    flagged_items: int
    issues: list[Issue] = field(default_factory=list)
    ready_to_send: bool = True


# ---------- IO helpers ----------

def load_json(path: str | None) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------- Security precheck ----------

def _is_generated(ans: dict) -> bool:
    return (ans.get("source") or "").lower() == "generated"


def precheck_security(
    responses: list[dict],
    approved_certs: list[dict] | None,
    approved_audits: list[dict] | None,
) -> GatePrecheck:
    sec_items = [r for r in responses if (r.get("domain") or "").lower() == "security"]
    pre = GatePrecheck(gate="security", total_items=len(sec_items), flagged_items=0)

    cert_names = {
        (c.get("name") or "").strip().lower()
        for c in (approved_certs or [])
        if (c.get("status") or "").lower() == "active"
    }
    audit_dates = {
        (a.get("cert") or "").strip().lower(): (a.get("audit_date") or "")
        for a in (approved_audits or [])
    }
    approved_algos = {
        "aes-256-gcm", "aes-256-cbc", "tls 1.2", "tls 1.3",
        "rsa-2048", "rsa-3072", "rsa-4096", "ecdsa p-256", "ecdsa p-384",
    }

    for item in sec_items:
        qid = item.get("id", "?")
        answer = (item.get("answer") or "").strip()
        if not answer:
            pre.issues.append(Issue(SEC_MISSING, "security", qid, "Empty answer."))
            continue

        if _is_generated(item) and not item.get("human_reviewed"):
            pre.issues.append(Issue(
                SEC_GENERATED_UNREVIEWED, "security", qid,
                "Generated content without human review.",
            ))

        for cert in (item.get("certifications_claimed") or []):
            name = (cert.get("name") or "").strip().lower()
            if name and name not in cert_names:
                pre.issues.append(Issue(
                    CERT_UNVERIFIED, "security", qid,
                    f"Cert '{cert.get('name')}' not in approved list.",
                ))
            audit_date = (cert.get("audit_date") or "").strip()
            if audit_date:
                expected = audit_dates.get(name)
                if expected and expected != audit_date:
                    pre.issues.append(Issue(
                        AUDIT_DATE_UNVERIFIED, "security", qid,
                        f"Audit date {audit_date} for {cert.get('name')} "
                        f"does not match approved {expected}.",
                    ))

        for algo in (item.get("crypto_claims") or []):
            if (algo or "").strip().lower() not in approved_algos:
                pre.issues.append(Issue(
                    CRYPTO_UNAPPROVED, "security", qid,
                    f"Algorithm '{algo}' not on approved list.",
                ))

    pre.flagged_items = len({i.question_id for i in pre.issues})
    pre.ready_to_send = not any(i.code in HARD_FAIL_CODES for i in pre.issues)
    return pre


# ---------- Legal precheck ----------

def precheck_legal(
    responses: list[dict],
    review_flags: dict | None,
    non_standard_terms: list[dict] | None,
) -> GatePrecheck:
    legal_items = [r for r in responses if (r.get("domain") or "").lower() == "legal"]
    pre = GatePrecheck(gate="legal", total_items=len(legal_items), flagged_items=0)
    flags = (review_flags or {}).get("legal", {}) if isinstance(review_flags, dict) else {}

    for item in legal_items:
        qid = item.get("id", "?")
        if not flags.get(qid, {}).get("human_reviewed"):
            pre.issues.append(Issue(
                LEGAL_UNREVIEWED, "legal", qid,
                "Legal response lacks human_reviewed=true.",
            ))
        level = (item.get("deviation_level") or "").lower()
        if level == "blocker" and not item.get("blocker_resolved"):
            pre.issues.append(Issue(
                LEGAL_BLOCKER, "legal", qid,
                "Unresolved Blocker-level deviation.",
            ))

    if not isinstance(non_standard_terms, list):
        pre.issues.append(Issue(
            LEGAL_NONSTANDARD_MISSING, "legal", "-",
            "Non-standard terms list not attached.",
            severity="hard",
        ))

    pre.flagged_items = len({i.question_id for i in pre.issues if i.question_id != "-"})
    pre.ready_to_send = not any(i.code in HARD_FAIL_CODES for i in pre.issues)
    return pre


# ---------- Pricing precheck ----------

def _tier_for(discount_pct: float, policy: dict) -> str:
    t = policy or {}
    if discount_pct <= t.get("standard_max", 10):
        return "Standard"
    if discount_pct <= t.get("managerial_max", 20):
        return "Managerial"
    if discount_pct <= t.get("vp_max", 30):
        return "VP"
    return "Exec"


def precheck_pricing(
    responses: list[dict],
    pricing_inputs: list[dict] | None,
    pricing_policy: dict | None,
) -> GatePrecheck:
    price_items = [r for r in responses if (r.get("domain") or "").lower() == "pricing"]
    pre = GatePrecheck(gate="pricing", total_items=len(price_items), flagged_items=0)
    now = datetime.now(timezone.utc)

    inputs_index = {
        (p.get("id") or ""): p for p in (pricing_inputs or [])
    }

    for item in price_items:
        qid = item.get("id", "?")
        if _is_generated(item):
            pre.issues.append(Issue(
                PRICING_GENERATED, "pricing", qid,
                "Pricing response has source=generated.",
            ))
            continue

        pid = item.get("pricing_input_id")
        if not pid:
            pre.issues.append(Issue(
                PRICING_UNLINKED, "pricing", qid,
                "Missing pricing_input_id.",
            ))
            continue
        if pid not in inputs_index:
            pre.issues.append(Issue(
                PRICING_INPUT_UNKNOWN, "pricing", qid,
                f"pricing_input_id '{pid}' not in authorised inputs.",
            ))
            continue
        if item.get("pricing_version") != inputs_index[pid].get("current_version"):
            pre.issues.append(Issue(
                PRICING_VERSION_STALE, "pricing", qid,
                f"Stale version for {pid}.",
            ))

        discount = float(item.get("discount_pct") or 0)
        tier = _tier_for(discount, pricing_policy or {})
        if tier != "Standard" and not item.get("authorisation_id"):
            pre.issues.append(Issue(
                PRICING_DISCOUNT_UNAUTHORISED, "pricing", qid,
                f"Discount {discount}% requires {tier}-tier authorisation.",
            ))

        if item.get("bundle") and not inputs_index[pid].get("bundle_authorised"):
            pre.issues.append(Issue(
                PRICING_BUNDLE_UNAUTHORISED, "pricing", qid,
                "Bundle not authorised.",
            ))

        validity = item.get("validity_until")
        if validity:
            try:
                if datetime.fromisoformat(validity.replace("Z", "+00:00")) < now:
                    pre.issues.append(Issue(
                        PRICING_EXPIRED, "pricing", qid,
                        f"Quote validity {validity} has passed.",
                    ))
            except ValueError:
                pre.issues.append(Issue(
                    PRICING_EXPIRED, "pricing", qid,
                    f"Unparseable validity_until: {validity}",
                ))

    pre.flagged_items = len({i.question_id for i in pre.issues})
    pre.ready_to_send = not any(i.code in HARD_FAIL_CODES for i in pre.issues)
    return pre


# ---------- Orchestration ----------

def build_report(
    responses: list[dict],
    approved_certs: list[dict] | None,
    approved_audits: list[dict] | None,
    review_flags: dict | None,
    non_standard_terms: list[dict] | None,
    pricing_inputs: list[dict] | None,
    pricing_policy: dict | None,
    response_source_bytes: bytes,
) -> dict:
    sec = precheck_security(responses, approved_certs, approved_audits)
    leg = precheck_legal(responses, review_flags, non_standard_terms)
    pri = precheck_pricing(responses, pricing_inputs, pricing_policy)
    all_issues = [asdict(i) for i in (sec.issues + leg.issues + pri.issues)]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "response_version_hash": sha256_bytes(response_source_bytes),
        "security_precheck": {**asdict(sec), "issues": [asdict(i) for i in sec.issues]},
        "legal_precheck": {**asdict(leg), "issues": [asdict(i) for i in leg.issues]},
        "pricing_precheck": {**asdict(pri), "issues": [asdict(i) for i in pri.issues]},
        "issues": all_issues,
        "ready_to_send": sec.ready_to_send and leg.ready_to_send and pri.ready_to_send,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="rfp-gates precheck")
    ap.add_argument("--responses", required=True)
    ap.add_argument("--approved-certs")
    ap.add_argument("--approved-audits")
    ap.add_argument("--pricing-inputs")
    ap.add_argument("--pricing-policy")
    ap.add_argument("--review-flags")
    ap.add_argument("--non-standard-terms")
    ap.add_argument("--output", required=True)
    args = ap.parse_args(argv)

    responses_path = Path(args.responses)
    if not responses_path.exists():
        print(f"ERROR: responses file not found: {args.responses}", file=sys.stderr)
        return 2

    with responses_path.open("rb") as f:
        raw = f.read()
    responses = json.loads(raw.decode("utf-8"))
    if isinstance(responses, dict) and "responses" in responses:
        responses = responses["responses"]

    report = build_report(
        responses=responses,
        approved_certs=load_json(args.approved_certs),
        approved_audits=load_json(args.approved_audits),
        review_flags=load_json(args.review_flags),
        non_standard_terms=load_json(args.non_standard_terms),
        pricing_inputs=load_json(args.pricing_inputs),
        pricing_policy=load_json(args.pricing_policy),
        response_source_bytes=raw,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    summary = (
        f"security: {report['security_precheck']['flagged_items']} flagged | "
        f"legal: {report['legal_precheck']['flagged_items']} flagged | "
        f"pricing: {report['pricing_precheck']['flagged_items']} flagged | "
        f"ready_to_send={report['ready_to_send']}"
    )
    print(summary)
    return 0 if report["ready_to_send"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

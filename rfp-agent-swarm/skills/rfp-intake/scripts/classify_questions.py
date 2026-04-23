#!/usr/bin/env python3
"""
classify_questions.py — Stage 2 of the rfp-intake pipeline.

Reads the raw output of parse_rfp.py and assigns each question a primary and
(optional) secondary category, an owner team, a mandatory flag, a word-limit
hint, and a confidence band.

Keyword signal lists below are illustrative, not exhaustive. They are
deliberately short and documented so they can be tuned as the swarm learns
from human corrections (captured by rfp-review). The authoritative taxonomy
lives in references/question-classification-taxonomy.md.

Python 3 stdlib only. Non-zero exit on fatal errors.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Signal dictionaries — short illustrative lists, to be tuned over time.
# ---------------------------------------------------------------------------
SIGNALS: dict[str, list[str]] = {
    "SEC": [
        "soc 2", "soc2", "iso 27001", "iso 27017", "iso 27018", "hipaa",
        "pci dss", "fedramp", "cyber essentials", "csa star", "caiq",
        "encryption at rest", "encryption in transit", "tls 1.2", "aes-256",
        "key management", "hsm", "byok", "penetration test", "pen test",
        "vulnerability scan", "sast", "dast", "bug bounty", "red team",
        "rbac", "least privilege", "mfa", "multi-factor", "privileged access",
        "pam", "siem", "24x7", "incident response", "breach notification",
        "rto", "rpo", "gdpr", "ccpa", "data residency", "dpa",
        "sub-processor", "nist 800-53", "cis controls", "ccm", "sig lite",
        "hecvat", "vsa", "secure sdlc", "sbom",
    ],
    "TEC": [
        "api", "rest", "graphql", "webhook", "sso", "saml", "oidc", "oauth2",
        "scim", "ldap", "multi-tenant", "single-tenant", "microservices",
        "event-driven", "reference architecture", "cloud", "on-prem",
        "hybrid", "private cloud", "air-gapped", "region",
        "availability zone", "latency", "throughput", "tps",
        "concurrent users", "load test", "benchmark", "sla", "uptime",
        "99.9", "99.95", "99.99", "failover", "disaster recovery",
        "data model", "schema", "etl", "streaming", "retention",
        "roadmap", "openapi", "swagger", "itil",
    ],
    "COM": [
        "pricing", "price", "per user", "per seat", "consumption", "tiered",
        "flat fee", "enterprise license", "ela", "volume discount",
        "multi-year discount", "ramp", "co-term", "payment terms", "net 30",
        "net 60", "invoicing", "billing", "msa", "sow", "order form",
        "term length", "auto-renewal", "termination for convenience",
        "service credits", "sla credits", "liquidated damages", "tco",
        "3-year tco", "5-year tco", "implementation cost",
        "professional services", "indemnification", "liability cap",
        "warranty",
    ],
    "COR": [
        "year founded", "headquarters", "ownership", "parent company",
        "number of employees", "revenue", "customer count",
        "countries served", "financial stability", "dun & bradstreet",
        "credit rating", "audited financials", "customer references",
        "case studies", "analogous clients", "gartner magic quadrant",
        "forrester wave", "idc marketscape", "diversity", "equity",
        "inclusion", "sustainability", "carbon", "net zero",
        "modern slavery", "cyber insurance", "professional liability",
        "aggregate limit",
    ],
    "GEN": [
        "submission format", "submission portal", "file format", "page limit",
        "font size", "q&a deadline", "clarification window",
        "oral presentation", "site visit", "point of contact", "spoc",
        "procurement contact", "proposal template", "cover letter",
        "executive summary", "response language", "mandatory attachments",
        "exhibits", "appendices",
    ],
}

OWNER_TEAM = {
    "SEC": "Security Engineering",
    "TEC": "Solution Architecture",
    "COM": "Commercial Desk",
    "COR": "Corporate Marketing",
    "GEN": "Bid Manager",
}

MANDATORY_TERMS = ("must", "shall", "is required", "is mandatory", "required to",
                   "at minimum", "no later than", "non-negotiable", "(m)",
                   "[required]")
OPTIONAL_TERMS = ("may ", "nice to have", "optional", "preferred but not required",
                  "if available", "(o)", "[optional]")

CREDENTIAL_TERMS = ("certified", "certification", "attested", "attestation", "accredited")
PRICING_TERMS = ("price", "pricing", "cost", "fee", "rate card", "quote")
LEGAL_TERMS = ("redline", "indemnif", "liability", "warranty", "governing law",
               "jurisdiction", "termination")
EVIDENCE_TERMS = ("exhibit", "appendix", "attachment", "please attach",
                  "provide a copy", "upload the")


def count_signals(text: str, signals: list[str]) -> list[str]:
    lower = text.lower()
    return [s for s in signals if s in lower]


def classify_one(text: str, section_hint: str) -> dict[str, Any]:
    scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for cat, terms in SIGNALS.items():
        matched = count_signals(text, terms)
        if matched:
            scores[cat] = len(matched)
            hits[cat] = matched

    # Section-heading override: a numbered section named "Security" etc. forces
    # that primary category regardless of signal density in the question text.
    section_lower = section_hint.lower() if section_hint else ""
    section_override = None
    for cat, tag in (("SEC", "security"), ("TEC", "technical"),
                     ("COM", "commercial"), ("COR", "company"),
                     ("GEN", "general")):
        if tag in section_lower:
            section_override = cat
            break

    if section_override:
        primary = section_override
    elif scores:
        primary = max(scores.items(), key=lambda kv: kv[1])[0]
    else:
        primary = "GEN"

    secondary = None
    if len(scores) >= 2:
        sorted_scores = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top, runner = sorted_scores[0], sorted_scores[1]
        if runner[1] >= 0.8 * top[1] and runner[0] != primary:
            secondary = runner[0]

    # Confidence banding
    total_signals = sum(scores.values())
    if section_override or (scores.get(primary, 0) >= 3 and not secondary):
        confidence = "HIGH"
    elif total_signals == 0:
        confidence = "LOW"
    else:
        confidence = "MEDIUM"

    needs_human_triage = confidence == "LOW" and not section_override

    # Mandatory / optional
    lower = text.lower()
    mandatory_hit = any(t in lower for t in MANDATORY_TERMS)
    optional_hit = any(t in lower for t in OPTIONAL_TERMS)
    if mandatory_hit:
        mandatory = True
    elif optional_hit and not mandatory_hit:
        mandatory = False
    else:
        mandatory = True  # default: bias toward answering

    # Flags
    credential_check = primary == "SEC" and any(t in lower for t in CREDENTIAL_TERMS)
    pricing = primary == "COM" and any(t in lower for t in PRICING_TERMS)
    legal_review = primary == "COM" and any(t in lower for t in LEGAL_TERMS)
    evidence_required = any(t in lower for t in EVIDENCE_TERMS)

    # Word-limit hint
    if re.search(r"yes\s*/\s*no", lower) or " y/n" in lower:
        word_limit_hint = 25
    elif any(s in lower for s in ("list", "enumerate", "provide a list")):
        word_limit_hint = 75
    elif any(s in lower for s in ("describe", "explain", "detail", "outline")):
        word_limit_hint = 250
    else:
        word_limit_hint = 150

    return {
        "primary_category": primary,
        "secondary_category": secondary,
        "owner_team": OWNER_TEAM[primary],
        "mandatory": mandatory,
        "confidence": confidence,
        "signal_hits": hits,
        "credential_check": credential_check,
        "pricing": pricing,
        "legal_review": legal_review,
        "evidence_required": evidence_required,
        "word_limit_hint": word_limit_hint,
        "needs_human_triage": needs_human_triage,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Classify parsed RFP questions")
    ap.add_argument("raw_json", help="Path to working/rfp_raw.json")
    ap.add_argument("--taxonomy", default="references/question-classification-taxonomy.md",
                    help="Path to taxonomy reference (read for documentation only)")
    ap.add_argument("--output", required=True, help="Path to write working/classified.json")
    args = ap.parse_args(argv)

    try:
        if not os.path.isfile(args.raw_json):
            print(f"ERROR: raw JSON not found: {args.raw_json}", file=sys.stderr)
            return 1
        with open(args.raw_json, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        classifications: list[dict[str, Any]] = []
        for q in raw.get("raw_questions", []):
            result = classify_one(q.get("text", ""), q.get("section", ""))
            result["question_id"] = q.get("question_id")
            classifications.append(result)

        # Summary counters
        by_cat: dict[str, int] = {}
        by_confidence: dict[str, int] = {}
        mandatory_count = 0
        triage_count = 0
        for c in classifications:
            by_cat[c["primary_category"]] = by_cat.get(c["primary_category"], 0) + 1
            by_confidence[c["confidence"]] = by_confidence.get(c["confidence"], 0) + 1
            if c["mandatory"]:
                mandatory_count += 1
            if c["needs_human_triage"]:
                triage_count += 1

        payload = {
            "rfp_id": raw.get("rfp_id"),
            "classifications": classifications,
            "summary": {
                "total": len(classifications),
                "by_category": by_cat,
                "by_confidence": by_confidence,
                "mandatory": mandatory_count,
                "needs_human_triage": triage_count,
            },
            "taxonomy_reference": args.taxonomy,
        }

        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

        print(json.dumps({
            "ok": True,
            "output": args.output,
            "summary": payload["summary"],
        }))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: classification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

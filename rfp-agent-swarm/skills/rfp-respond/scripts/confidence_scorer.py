#!/usr/bin/env python3
"""
confidence_scorer.py

Canonical tier + confidence scorer for rfp-respond. Deterministic; no
external services. Thresholds are taken from
references/confidence-tier-rules.md.

Input:
  --search-result   path to working/bank_search_results.json

Output:
  --output          path to write working/confidence.json
  Also emits JSON to stdout.

Rules enforced:
  - Tier from reranker score (>= 0.90 HIGH, 0.75..0.89 MEDIUM, else LOW).
  - Adjustments (additive, bounded): category match, freshness, staleness,
    length similarity, framework mismatch.
  - If source == "GENERATED", confidence is capped at 75.
  - Deprecated bank entries are skipped.

Python 3 stdlib only.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

HIGH_THRESHOLD = 0.90
MEDIUM_THRESHOLD = 0.75
GENERATED_CAP = 75

FRAMEWORK_TOKENS = (
    "soc 2", "soc2", "iso 27001", "iso27001", "gdpr", "hipaa",
    "pci-dss", "pci dss", "fedramp", "nist", "uk dpa", "lgpd",
)


def load_json(path):
    if not os.path.exists(path):
        sys.stderr.write(f"ERROR: missing input: {path}\n")
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def tier_for_score(score):
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def category_match_bonus(question, candidate):
    q = set(question.get("tags", []))
    c = set(candidate.get("tags", []))
    return 5 if q & c else 0


def freshness_adjustments(candidate):
    d = parse_date(candidate.get("last_approved_date"))
    if d is None:
        return 0, 0
    now = datetime.now(tz=timezone.utc)
    months_old = (now - d).days / 30.0
    fresh_bonus = 3 if months_old <= 6 else 0
    staleness_penalty = -6 if months_old > 18 else 0
    return fresh_bonus, staleness_penalty


def length_similarity_bonus(question, candidate):
    q_len = len((question.get("text") or ""))
    c_len = len((candidate.get("original_question") or ""))
    if not q_len or not c_len:
        return 0
    delta = abs(q_len - c_len) / max(q_len, c_len)
    return 2 if delta < 0.30 else 0


def framework_mismatch_penalty(question, candidate):
    qtext = (question.get("text") or "").lower()
    frameworks_in_q = {t for t in FRAMEWORK_TOKENS if t in qtext}
    if not frameworks_in_q:
        return 0
    # Search candidate text and tags for any mentioned framework
    ctext = " ".join([
        (candidate.get("response_text") or ""),
        (candidate.get("original_question") or ""),
        " ".join(candidate.get("tags", [])),
    ]).lower()
    for fw in frameworks_in_q:
        if fw in ctext:
            return 0
    return -10


def pick_top_candidate(candidates):
    filtered = [c for c in candidates if not c.get("deprecated", False)]
    if not filtered:
        return None
    filtered.sort(
        key=lambda c: (
            -float(c.get("reranker_score", 0.0)),
            -(parse_date(c.get("last_approved_date"))
              or datetime(1970, 1, 1, tzinfo=timezone.utc)).timestamp(),
            c.get("bank_entry_id", "ZZZ"),
        )
    )
    return filtered[0]


def score_question(question, candidates, source_hint=None):
    cand = pick_top_candidate(candidates)
    if cand is None:
        return {
            "question_id": question["question_id"],
            "reranker_score": 0.0,
            "tier": "LOW",
            "confidence": 0,
            "adjustments": {
                "category_match_bonus": 0,
                "freshness_bonus": 0,
                "staleness_penalty": 0,
                "length_similarity_bonus": 0,
                "framework_mismatch_penalty": 0,
            },
            "rationale": "no candidate returned from bank search",
            "source": "GENERATED",
        }

    raw_score = float(cand.get("reranker_score", 0.0))
    # Guard against NaN / out-of-range scores
    if not (0.0 <= raw_score <= 1.0):
        sys.stderr.write(
            f"WARN: reranker score out of range for {question['question_id']};"
            f" treating as 0.0\n"
        )
        raw_score = 0.0

    base = raw_score * 100.0
    cat = category_match_bonus(question, cand)
    fresh, stale = freshness_adjustments(cand)
    length = length_similarity_bonus(question, cand)
    fw = framework_mismatch_penalty(question, cand)

    confidence = int(round(max(0, min(100, base + cat + fresh + stale
                                       + length + fw))))

    tier = tier_for_score(raw_score)

    # Effective source: if the upstream drafter signalled a generated source,
    # OR the tier is LOW (which will trigger generation), apply the cap.
    source = source_hint or ("GENERATED" if tier == "LOW"
                             else cand.get("bank_entry_id"))

    if str(source).startswith("GENERATED"):
        confidence = min(confidence, GENERATED_CAP)

    return {
        "question_id": question["question_id"],
        "reranker_score": raw_score,
        "tier": tier,
        "confidence": confidence,
        "adjustments": {
            "category_match_bonus": cat,
            "freshness_bonus": fresh,
            "staleness_penalty": stale,
            "length_similarity_bonus": length,
            "framework_mismatch_penalty": fw,
        },
        "rationale": (
            f"reranker {raw_score:.2f}; cat+{cat}; fresh+{fresh}; "
            f"stale{stale}; len+{length}; fw{fw}"
        ),
        "source": source,
        "bank_entry_id": cand.get("bank_entry_id"),
        "last_approved_date": cand.get("last_approved_date"),
    }


def main():
    p = argparse.ArgumentParser(description="Score confidence tiers.")
    p.add_argument("--search-result", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    data = load_json(args.search_result)
    results = data.get("results", [])
    scored = []
    for item in results:
        question = item.get("question", {"question_id": item.get("question_id"),
                                         "text": "", "tags": []})
        candidates = item.get("candidates", [])
        scored.append(score_question(question, candidates))

    out = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(scored),
        "scores": scored,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

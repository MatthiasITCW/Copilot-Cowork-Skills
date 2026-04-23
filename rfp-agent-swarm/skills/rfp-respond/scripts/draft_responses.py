#!/usr/bin/env python3
"""
draft_responses.py

Orchestrates per-question drafting for rfp-respond (Step 3 of the RFP Agent
Swarm). Deterministic decision tree only: no AI generation happens here. For
LOW-tier questions the script emits a placeholder with a FLAG_FOR_GENERATION
marker that the downstream AI caller fills in (and then re-runs confidence
scoring to confirm the cap at 75 holds).

Inputs:
  --task-list             path to working/task_list.json (from rfp-intake)
  --bank-search-results   path to working/bank_search_results.json
                          (produced upstream by one call per question to
                           rfp-answer-bank/scripts/search_bank.py)
  --output                path to write working/responses.json

Outputs:
  - JSON to stdout (same content as --output)
  - Exit 0 on success, non-zero on missing-input or integrity error

Python 3 stdlib only.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

# Banned-phrase guardrail. Kept short here; full list in
# references/tone-and-style-guide.md. Hits become a style_flag on the row.
BANNED_PHRASES = [
    "world-class", "industry-leading", "best-in-class", "cutting-edge",
    "state-of-the-art", "seamless", "peace of mind", "turnkey",
    "military-grade", "bank-grade", "unparalleled", "holistic", "synergy",
]

# Allowed MEDIUM edits that record a delta but are permitted. See
# references/retrieval-first-playbook.md §4.
ALLOWED_MEDIUM_EDIT_TYPES = {
    "tighten", "specialise", "trim", "reorder", "stitch",
}

HIGH_THRESHOLD = 0.90
MEDIUM_THRESHOLD = 0.75
GENERATED_CAP = 75


def load_json(path):
    if not os.path.exists(path):
        sys.stderr.write(f"ERROR: missing input: {path}\n")
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def tier_for_score(score):
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def pick_top_candidate(candidates):
    """Pick the freshest candidate among those sharing the top reranker score.

    Deterministic: freshest last_approved_date wins; ties broken by
    lexicographically smallest bank_entry_id.
    """
    if not candidates:
        return None
    filtered = [c for c in candidates if not c.get("deprecated", False)]
    if not filtered:
        return None
    filtered.sort(
        key=lambda c: (
            -float(c.get("reranker_score", 0.0)),
            -_date_key(c.get("last_approved_date", "1970-01-01")),
            c.get("bank_entry_id", "ZZZ"),
        )
    )
    return filtered[0]


def _date_key(iso):
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").timestamp()
    except (ValueError, TypeError):
        return 0.0


def detect_banned_phrases(text):
    lowered = text.lower()
    return sorted({p for p in BANNED_PHRASES if p in lowered})


def is_held_category(question):
    """Pricing / legal-signoff / cert-invention categories are held, not
    generated, when no strong match exists."""
    tags = set(question.get("tags", []))
    holds = {"pricing", "legal-signoff", "certification-claim"}
    return bool(tags & holds)


def primary_team(question):
    """Deterministic primary-team rule. Mirrors route_to_specialists.py."""
    tags = set(question.get("tags", []))
    if "pricing" in tags or "legal" in tags or "commercial" in tags:
        return "commercial"
    if "security" in tags or "compliance" in tags:
        return "security"
    if "technical" in tags or "integration" in tags:
        return "technical"
    return "commercial"  # default owner for un-tagged catch-alls


def build_high_row(q, cand, scored):
    return {
        "question_id": q["question_id"],
        "team": primary_team(q),
        "consulted_teams": q.get("consulted_teams", []),
        "tier": "HIGH",
        "confidence": scored["confidence"],
        "response_text": cand["response_text"],
        "source": {
            "bank_entry_id": cand["bank_entry_id"],
            "last_approved_date": cand.get("last_approved_date"),
            "original_question": cand.get("original_question"),
            "delta_summary": "",
        },
        "flags": [],
        "reviewer_required": False,
        "style_flags": detect_banned_phrases(cand["response_text"]),
    }


def build_medium_row(q, cand, scored):
    # The script does not perform the adaptation text-edit here; it marks the
    # row ADAPT_REQUIRED and records the candidate's text as the seed. The
    # team agent performs the allowed edits and then the row is re-validated.
    return {
        "question_id": q["question_id"],
        "team": primary_team(q),
        "consulted_teams": q.get("consulted_teams", []),
        "tier": "MEDIUM",
        "confidence": scored["confidence"],
        "response_text": cand["response_text"],  # seed; will be adapted
        "source": {
            "bank_entry_id": cand["bank_entry_id"],
            "last_approved_date": cand.get("last_approved_date"),
            "original_question": cand.get("original_question"),
            "delta_summary": "ADAPT_REQUIRED",
        },
        "flags": ["ADAPT_REQUIRED"],
        "reviewer_required": True,
        "style_flags": detect_banned_phrases(cand["response_text"]),
    }


def build_low_row(q, cand, scored):
    seed_id = cand["bank_entry_id"] if cand else None
    held = is_held_category(q)
    flags = ["REVIEWER_REQUIRED"]
    if held:
        flags.append("NEEDS_AUTHORISED_INPUT")
        response_text = (
            "[HELD] This question requires authorised inputs from the "
            "commercial / legal / compliance owner and is not drafted by "
            "retrieval or generation."
        )
    else:
        flags.append("FLAG_FOR_GENERATION")
        response_text = (
            "[TO BE GENERATED — placeholder] Preamble from "
            "assets/response-preamble-template.md will be prepended. "
            "Confidence is capped at 75."
        )

    return {
        "question_id": q["question_id"],
        "team": primary_team(q),
        "consulted_teams": q.get("consulted_teams", []),
        "tier": "LOW",
        "confidence": min(scored["confidence"], GENERATED_CAP),
        "response_text": response_text,
        "source": {
            "bank_entry_id": "GENERATED" + (f"+{seed_id}" if seed_id else ""),
            "last_approved_date": cand.get("last_approved_date") if cand else None,
            "original_question": None,
            "delta_summary": "",
            "generation_seed": (
                "no_bank_match" if not cand else f"weak_match:{seed_id}"
            ),
        },
        "flags": flags,
        "reviewer_required": True,
        "style_flags": [],
    }


def score_for_candidate(cand, question):
    """Simplified local scoring that mirrors confidence_scorer.py. The
    canonical scorer should be called separately; this inline version keeps
    the drafter runnable in isolation for deterministic pipeline tests."""
    if cand is None:
        return {"confidence": 0, "rationale": "no candidate"}
    score = float(cand.get("reranker_score", 0.0))
    base = score * 100.0

    # category match
    q_cat = set(question.get("tags", []))
    c_cat = set(cand.get("tags", []))
    cat_bonus = 5 if q_cat & c_cat else 0

    # freshness
    approved = cand.get("last_approved_date", "1970-01-01")
    fresh_bonus = 0
    staleness_penalty = 0
    try:
        d = datetime.strptime(approved[:10], "%Y-%m-%d").replace(
            tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        months_old = (now - d).days / 30.0
        if months_old <= 6:
            fresh_bonus = 3
        elif months_old > 18:
            staleness_penalty = -6
    except (ValueError, TypeError):
        pass

    # length similarity
    q_len = len((question.get("text") or ""))
    c_len = len((cand.get("original_question") or ""))
    length_bonus = 0
    if q_len and c_len and abs(q_len - c_len) / max(q_len, c_len) < 0.30:
        length_bonus = 2

    confidence = int(round(
        max(0, min(100, base + cat_bonus + fresh_bonus + staleness_penalty
                   + length_bonus))
    ))

    return {
        "confidence": confidence,
        "rationale": (
            f"reranker {score:.2f} cat+{cat_bonus} fresh+{fresh_bonus} "
            f"stale{staleness_penalty} len+{length_bonus}"
        ),
    }


def draft(task_list, bank_search_results):
    by_qid = {r["question_id"]: r for r in bank_search_results.get("results", [])}
    rows = []
    for q in task_list.get("questions", []):
        qid = q["question_id"]
        search = by_qid.get(qid, {"candidates": []})
        cand = pick_top_candidate(search.get("candidates", []))
        score = cand.get("reranker_score", 0.0) if cand else 0.0
        tier = tier_for_score(score)
        scored = score_for_candidate(cand, q)

        if tier == "HIGH":
            row = build_high_row(q, cand, scored)
        elif tier == "MEDIUM":
            row = build_medium_row(q, cand, scored)
        else:
            row = build_low_row(q, cand, scored)

        # Integrity check: generated must not exceed cap.
        if row["source"]["bank_entry_id"].startswith("GENERATED"):
            if row["confidence"] > GENERATED_CAP:
                sys.stderr.write(
                    f"INTEGRITY ERROR: generated row {qid} exceeds cap\n")
                sys.exit(3)

        rows.append(row)

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "count": len(rows),
        "responses": rows,
    }


def main():
    p = argparse.ArgumentParser(description="Draft RFP responses per question.")
    p.add_argument("--task-list", required=True)
    p.add_argument("--bank-search-results", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    tl = load_json(args.task_list)
    bs = load_json(args.bank_search_results)

    out = draft(tl, bs)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

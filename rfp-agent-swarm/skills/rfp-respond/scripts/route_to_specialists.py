#!/usr/bin/env python3
"""
route_to_specialists.py

Partitions the RFP task list into team queues (Security / Technical /
Commercial) and a shared queue for multi-team questions. Emits a manifest
with per-team estimated effort and an imbalance warning when one team's
load exceeds 2x another's.

Enables parallel downstream processing (Step 3 of the RFP Agent Swarm).

Input:
  --task-list   path to working/task_list.json (from rfp-intake)

Output:
  --output      path to write working/team_queues.json
  Also emits JSON to stdout.

Deterministic rules:
  - Primary-team resolution table in references/team-specialist-guides.md §4
  - Pricing / legal tags force commercial PRIMARY
  - Effort estimate = base(1) + length_factor + tag_complexity_factor

Python 3 stdlib only.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

TEAMS = ("security", "technical", "commercial")

# Tag -> team mapping. A question may carry several tags.
TAG_TO_TEAM = {
    # security
    "security": "security",
    "compliance": "security",
    "privacy": "security",
    "audit": "security",
    "pentest": "security",
    "encryption": "security",
    "vulnerability": "security",
    # technical
    "technical": "technical",
    "feature": "technical",
    "architecture": "technical",
    "deployment": "technical",
    "sla": "technical",
    "api": "technical",
    "sso": "technical",
    "scim": "technical",
    "migration": "technical",
    "performance": "technical",
    "integration": "technical",
    # commercial
    "commercial": "commercial",
    "company": "commercial",
    "reference": "commercial",
    "case-study": "commercial",
    "pricing": "commercial",
    "msa": "commercial",
    "dpa": "commercial",
    "legal": "commercial",
    "terms": "commercial",
}

# If a question carries any of these, commercial is forced as PRIMARY.
FORCE_COMMERCIAL_PRIMARY = {"pricing", "legal", "msa", "terms"}

# Multi-team resolution: (frozenset of involved teams) -> primary
MULTI_TEAM_PRIMARY = {
    frozenset({"security", "technical"}): "security",
    frozenset({"security", "commercial"}): "commercial",
    frozenset({"technical", "commercial"}): "commercial",
    frozenset({"security", "technical", "commercial"}): "security",
}


def load_json(path):
    if not os.path.exists(path):
        sys.stderr.write(f"ERROR: missing input: {path}\n")
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def teams_for_tags(tags):
    """Return the set of teams implied by a question's tags."""
    teams = set()
    for t in tags:
        tgt = TAG_TO_TEAM.get(t)
        if tgt:
            teams.add(tgt)
    return teams


def resolve_primary_and_consulted(question):
    tags = list(question.get("tags", []))
    force = set(tags) & FORCE_COMMERCIAL_PRIMARY
    teams = teams_for_tags(tags)

    if not teams:
        # Un-tagged catch-all: default to commercial (company overview etc.)
        return "commercial", []

    if force:
        primary = "commercial"
    elif len(teams) == 1:
        primary = next(iter(teams))
    else:
        primary = MULTI_TEAM_PRIMARY.get(frozenset(teams), "commercial")

    consulted = sorted(t for t in teams if t != primary)
    return primary, consulted


def estimate_effort(question):
    """Lightweight effort score (arbitrary units). Used only for load
    balancing warnings; not consumed downstream for scheduling."""
    base = 1.0
    text = question.get("text", "") or ""
    length_factor = min(len(text) / 400.0, 4.0)
    tag_count = len(question.get("tags", []))
    complexity = min(tag_count * 0.25, 1.5)
    # Pricing and legal tend to need human cycles — bump.
    if set(question.get("tags", [])) & FORCE_COMMERCIAL_PRIMARY:
        complexity += 1.0
    return round(base + length_factor + complexity, 2)


def route(task_list):
    queues = {t: [] for t in TEAMS}
    shared = []
    totals = {t: 0.0 for t in TEAMS}

    for q in task_list.get("questions", []):
        primary, consulted = resolve_primary_and_consulted(q)
        effort = estimate_effort(q)

        record = {
            "question_id": q["question_id"],
            "primary_team": primary,
            "consulted_teams": consulted,
            "effort": effort,
            "tags": q.get("tags", []),
        }

        queues[primary].append(record)
        totals[primary] += effort

        if consulted:
            shared.append(record)

    # Imbalance warning: max / min > 2
    nonzero = [v for v in totals.values() if v > 0]
    imbalance_warning = False
    imbalance_detail = None
    if len(nonzero) >= 2:
        hi = max(totals.values())
        lo = min(v for v in totals.values() if v > 0)
        if lo > 0 and hi / lo > 2.0:
            imbalance_warning = True
            imbalance_detail = {
                "max_team": max(totals, key=totals.get),
                "max_effort": round(hi, 2),
                "min_team": min(totals, key=lambda k: totals[k] if totals[k] > 0
                                else float("inf")),
                "min_effort": round(lo, 2),
                "ratio": round(hi / lo, 2),
            }

    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "totals": {t: round(v, 2) for t, v in totals.items()},
        "counts": {t: len(queues[t]) for t in TEAMS},
        "shared_count": len(shared),
        "imbalance_warning": imbalance_warning,
        "imbalance_detail": imbalance_detail,
        "queues": queues,
        "shared_queue": shared,
    }
    return manifest


def main():
    p = argparse.ArgumentParser(description="Route questions to team queues.")
    p.add_argument("--task-list", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    tl = load_json(args.task_list)
    manifest = route(tl)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)

    json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

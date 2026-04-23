#!/usr/bin/env python3
"""generate_go_no_go_memo.py

Deterministic template substitution. Reads the Go/No-Go memo template
from assets/, merges values from fit_result.json, kb_match_estimate.json,
and rfp_metadata.json, and writes a finished markdown memo that is ready
to feed into the docx built-in for a Word export.

NO freeform AI content is generated here. If a value is missing, the
corresponding [PLACEHOLDER] token stays in place and the script exits
with code 3 so the upstream pipeline can fix the data.

USAGE:
  python scripts/generate_go_no_go_memo.py \
      --fit working/fit_result.json \
      --kb  working/kb_match_estimate.json \
      --metadata working/rfp_metadata.json \
      --template assets/go-no-go-memo-template.md \
      --output working/go_no_go_memo.md

Expected placeholders in the template (exact strings):
  [RFP_TITLE] [BUYER_NAME] [DEADLINE] [OVERALL_SCORE] [RECOMMENDATION]
  [KB_MATCH_PCT] [KB_CONFIDENCE] [TECHNICAL_FIT] [COMMERCIAL_FIT]
  [COMPETITIVE_FIT] [STRATEGIC_FIT] [RESOURCE_FIT] [DEADLINE_FIT]
  [TOP_RISKS_BULLETS] [MITIGATIONS_BULLETS]
  [KILL_CRITERIA_BULLETS] [SME_HOURS_ESTIMATE]
  [DECISION_OWNER] [GENERATED_AT]

Stdlib only. No network.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIM_LABEL = {
    "kb_match": "KB_MATCH",
    "technical_fit": "TECHNICAL_FIT",
    "commercial_fit": "COMMERCIAL_FIT",
    "competitive": "COMPETITIVE_FIT",
    "strategic": "STRATEGIC_FIT",
    "resource": "RESOURCE_FIT",
    "deadline": "DEADLINE_FIT",
}


def _fail(message: str, code: int = 2) -> None:
    print(json.dumps({"error": message}), file=sys.stderr)
    sys.exit(code)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        _fail(f"{label} not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        _fail(f"{label} JSON invalid: {exc}")
    return {}


def _band_display(band: str) -> str:
    return {
        "GO": "Recommend GO (advisory)",
        "CONDITIONAL": "CONDITIONAL — AE clarifications required",
        "NO_GO": "Recommend NO-GO (advisory)",
    }.get(band, band)


def _bullets(items: list[str], empty_text: str = "- (none)") -> str:
    if not items:
        return empty_text
    return "\n".join(f"- {s}" for s in items)


def _risk_bullets(risks: list[dict[str, Any]]) -> str:
    rows = []
    for r in risks:
        dim = r.get("dimension", "?")
        sev = r.get("severity", "MEDIUM")
        note = r.get("note", "")
        rows.append(f"{sev} — {dim}: {note}")
    return _bullets(rows, "- No dimensions scored below 3.")


def _kill_bullets(flagged: list[dict[str, Any]]) -> str:
    if not flagged:
        return "- None"
    return "\n".join(
        f"- KILL CRITERION — HUMAN REVIEW: "
        f"{k.get('id', '?')} — {k.get('description', '')}"
        for k in flagged
    )


def _contribution_lookup(
    contribs: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    return {c["dimension"]: c for c in contribs}


def build_substitutions(
    fit: dict[str, Any],
    kb: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, str]:
    contribs = _contribution_lookup(fit.get("contributions", []))

    def dim_display(dim_key: str) -> str:
        c = contribs.get(dim_key)
        if not c:
            return "n/a"
        return f"{c['raw']}/5 (value {c['value']}, contrib {c['contribution']})"

    # Mitigations surface from metadata.mitigations or empty
    mitigations = metadata.get("mitigations") or []
    if not isinstance(mitigations, list):
        mitigations = []

    subs: dict[str, str] = {
        "[RFP_TITLE]": str(metadata.get("title", "UNKNOWN RFP")),
        "[BUYER_NAME]": str(metadata.get("buyer", "UNKNOWN BUYER")),
        "[DEADLINE]": str(metadata.get("deadline", "UNKNOWN")),
        "[OVERALL_SCORE]": f"{fit.get('weighted_total', '?')}",
        "[RECOMMENDATION]": _band_display(str(fit.get("band", "?"))),
        "[KB_MATCH_PCT]": f"{kb.get('overall_estimate_pct', '?')}%",
        "[KB_CONFIDENCE]": str(kb.get("confidence", "?")),
        "[TECHNICAL_FIT]": dim_display("technical_fit"),
        "[COMMERCIAL_FIT]": dim_display("commercial_fit"),
        "[COMPETITIVE_FIT]": dim_display("competitive"),
        "[STRATEGIC_FIT]": dim_display("strategic"),
        "[RESOURCE_FIT]": dim_display("resource"),
        "[DEADLINE_FIT]": dim_display("deadline"),
        "[TOP_RISKS_BULLETS]": _risk_bullets(fit.get("risks", [])),
        "[MITIGATIONS_BULLETS]": _bullets(
            [str(m) for m in mitigations],
            "- (AE to propose mitigations before sign-off)",
        ),
        "[KILL_CRITERIA_BULLETS]": _kill_bullets(
            fit.get("kill_criteria_flagged", [])
        ),
        "[SME_HOURS_ESTIMATE]": str(
            metadata.get("sme_hours_estimate", "TBD")
        ),
        "[DECISION_OWNER]": str(metadata.get("decision_owner", "VP Sales")),
        "[GENERATED_AT]": datetime.now(timezone.utc).isoformat(),
    }
    return subs


def substitute(template: str, subs: dict[str, str]) -> tuple[str, list[str]]:
    out = template
    for token, value in subs.items():
        out = out.replace(token, value)
    # Find any remaining [ALL_CAPS_TOKEN]
    remaining = sorted(set(re.findall(r"\[[A-Z0-9_]+\]", out)))
    return out, remaining


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Go/No-Go memo via deterministic substitution."
    )
    parser.add_argument("--fit", required=True, type=Path)
    parser.add_argument("--kb", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fit = _load_json(args.fit, "fit")
    kb = _load_json(args.kb, "kb")
    metadata = _load_json(args.metadata, "metadata")

    if not args.template.exists():
        _fail(f"template not found: {args.template}")
    template = args.template.read_text(encoding="utf-8")

    subs = build_substitutions(fit, kb, metadata)
    rendered, remaining = substitute(template, subs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    result = {
        "output": str(args.output),
        "bytes": len(rendered),
        "unresolved_placeholders": remaining,
        "recommendation": fit.get("band"),
        "weighted_total": fit.get("weighted_total"),
    }
    print(json.dumps(result, indent=2))

    if remaining:
        # Non-zero exit so pipelines don't silently ship a memo with
        # literal [PLACEHOLDER] tokens left in it.
        print(
            "WARNING: unresolved placeholders remain in memo: "
            + ", ".join(remaining),
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

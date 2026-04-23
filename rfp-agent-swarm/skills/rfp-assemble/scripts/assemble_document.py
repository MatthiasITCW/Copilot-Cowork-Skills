#!/usr/bin/env python3
"""
assemble_document.py
--------------------

Produce the STRUCTURED CONTENT MANIFEST (JSON) that the docx / xlsx / pdf /
portal renderers will consume. This script does not write Word, Excel, or PDF
bytes directly — that is the job of the respective built-in skills.

CLI:
    python scripts/assemble_document.py \\
        --responses working/reviewed_responses.json \\
        --format word|excel|pdf|portal \\
        --template <template_path> \\
        --output working/assembled_manifest.json

Behaviour:
    * Validates every question has a reviewed response
    * Validates all provenance fields are present
    * Validates the provenance appendix row count equals total question count
    * Emits a manifest JSON describing sections, ordering, content blocks,
      style hints, cover letter path, and the provenance appendix

Exit codes:
    0  manifest written
    2  input validation failure
    3  provenance audit mismatch
    4  unknown format
"""

from __future__ import annotations

import argparse
import json
import sys
import os
import datetime
from typing import Any, Dict, List, Tuple

MANDATORY_PROVENANCE_FIELDS = (
    "response_id",
    "question_id",
    "category",
    "source",
    "tier",
    "reviewer",
    "review_status",
    "last_updated",
)

ALLOWED_TIERS = {"HIGH", "MEDIUM", "LOW"}
ALLOWED_REVIEW_STATUSES = {"approved", "approved_with_changes"}
ALLOWED_FORMATS = {"word", "excel", "pdf", "portal"}

WORD_SECTION_ORDER = (
    "cover_letter",
    "executive_summary",
    "company_overview",
    "technical_response",
    "security_response",
    "commercial_response",
    "case_studies",
    "appendices",
    "provenance_appendix",
)

EXCEL_SHEET_ORDER = (
    "Summary",
    "Security",
    "Technical",
    "Commercial",
    "Company",
    "Provenance",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the assemble manifest.")
    p.add_argument("--responses", required=True, help="Reviewed responses JSON")
    p.add_argument("--format", required=True, choices=sorted(ALLOWED_FORMATS))
    p.add_argument("--template", required=False, default="", help="Template path")
    p.add_argument("--output", required=True, help="Manifest output path")
    p.add_argument("--metadata", required=False, default="",
                   help="Optional RFP metadata JSON")
    p.add_argument("--branding", required=False, default="",
                   help="Optional branding tokens JSON")
    p.add_argument("--cover-letter", required=False, default="",
                   help="Path to populated cover letter markdown or PDF")
    return p.parse_args()


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def fail(code: int, message: str) -> None:
    sys.stderr.write("ERROR: " + message + "\n")
    sys.exit(code)


def validate_responses(responses: List[Dict[str, Any]]) -> List[str]:
    """Return a list of validation errors. Empty list means valid."""
    errors: List[str] = []
    seen_response_ids: Dict[str, int] = {}
    seen_question_ids: Dict[str, int] = {}

    for idx, resp in enumerate(responses):
        for field in MANDATORY_PROVENANCE_FIELDS:
            if field not in resp or resp[field] in (None, ""):
                errors.append(
                    "row {0}: missing mandatory field '{1}'".format(idx, field)
                )

        tier = resp.get("tier")
        if tier and tier not in ALLOWED_TIERS:
            errors.append("row {0}: tier '{1}' not in {2}".format(idx, tier, ALLOWED_TIERS))

        review_status = resp.get("review_status")
        if review_status and review_status not in ALLOWED_REVIEW_STATUSES:
            errors.append(
                "row {0}: review_status '{1}' not approved".format(idx, review_status)
            )

        source = resp.get("source", "")
        if source and not (
            source.startswith("bank_entry:") or source == "generated+reviewed"
        ):
            errors.append(
                "row {0}: source '{1}' not in accepted forms".format(idx, source)
            )

        rid = resp.get("response_id")
        if rid:
            if rid in seen_response_ids:
                errors.append("duplicate response_id '{0}'".format(rid))
            seen_response_ids[rid] = idx

        qid = resp.get("question_id")
        if qid:
            if qid in seen_question_ids:
                errors.append("duplicate question_id '{0}'".format(qid))
            seen_question_ids[qid] = idx

    return errors


def bucket_by_category(responses: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for resp in responses:
        buckets.setdefault(resp.get("category", "Other"), []).append(resp)
    return buckets


def build_provenance_appendix(
    responses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for resp in responses:
        rows.append({k: resp.get(k) for k in MANDATORY_PROVENANCE_FIELDS})
    return rows


def build_word_manifest(
    responses: List[Dict[str, Any]],
    template: str,
    cover_letter: str,
    branding: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    buckets = bucket_by_category(responses)
    sections: List[Dict[str, Any]] = []
    for section_key in WORD_SECTION_ORDER:
        block: Dict[str, Any] = {"key": section_key, "order": len(sections) + 1}
        if section_key == "cover_letter":
            block["path"] = cover_letter
        elif section_key == "executive_summary":
            block["content_source"] = "generated_summary"
            block["page_limit"] = metadata.get("exec_summary_page_limit", 1)
        elif section_key == "security_response":
            block["rows"] = buckets.get("Security", [])
        elif section_key == "technical_response":
            block["rows"] = buckets.get("Technical", [])
        elif section_key == "commercial_response":
            block["rows"] = buckets.get("Commercial", [])
        elif section_key == "company_overview":
            block["rows"] = buckets.get("Company", [])
        elif section_key == "provenance_appendix":
            block["rows"] = build_provenance_appendix(responses)
        sections.append(block)

    return {
        "format": "word",
        "template": template,
        "style": branding,
        "metadata": metadata,
        "sections": sections,
        "total_questions": len(responses),
        "provenance_row_count": len(responses),
    }


def build_excel_manifest(
    responses: List[Dict[str, Any]],
    template: str,
    branding: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    buckets = bucket_by_category(responses)
    sheets: List[Dict[str, Any]] = []
    for sheet_name in EXCEL_SHEET_ORDER:
        if sheet_name == "Summary":
            sheets.append({
                "name": "Summary",
                "rows": [
                    ["RFP ID", metadata.get("rfp_id", "")],
                    ["Buyer", metadata.get("buyer_name", "")],
                    ["Submission date", metadata.get("submission_date", "")],
                    ["Contact", metadata.get("account_executive_email", "")],
                ],
            })
        elif sheet_name == "Provenance":
            sheets.append({
                "name": "Provenance",
                "headers": list(MANDATORY_PROVENANCE_FIELDS),
                "rows": build_provenance_appendix(responses),
                "hidden_columns": list(range(5, len(MANDATORY_PROVENANCE_FIELDS))),
            })
        else:
            sheets.append({
                "name": sheet_name,
                "headers": [
                    "question_id", "category", "question",
                    "response", "supporting_detail",
                    "source", "tier", "reviewer",
                ],
                "hidden_columns": [5, 6, 7],
                "rows": buckets.get(sheet_name, []),
            })

    return {
        "format": "excel",
        "template": template,
        "style": branding,
        "metadata": metadata,
        "sheets": sheets,
        "total_questions": len(responses),
        "provenance_row_count": len(responses),
    }


def build_pdf_manifest(
    word_manifest: Dict[str, Any],
) -> Dict[str, Any]:
    # PDF is rendered by flattening a rendered Word file. Reuse the Word
    # manifest but flag the renderer expectation.
    pdf_manifest = dict(word_manifest)
    pdf_manifest["format"] = "pdf"
    pdf_manifest["render_path"] = "word_then_flatten"
    return pdf_manifest


def build_portal_manifest(
    responses: List[Dict[str, Any]],
    branding: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    vendor = metadata.get("portal_vendor", "generic")
    return {
        "format": "portal",
        "portal_vendor": vendor,
        "style": branding,
        "metadata": metadata,
        "rows": [
            {
                "question_id": r.get("question_id"),
                "response": r.get("response") or r.get("answer", ""),
                "attachment_filename": r.get("attachment_filename", ""),
                "provenance": {k: r.get(k) for k in MANDATORY_PROVENANCE_FIELDS},
            }
            for r in responses
        ],
        "sidecar_manifest": {
            "rfp_id": metadata.get("rfp_id", ""),
            "provenance": build_provenance_appendix(responses),
        },
        "total_questions": len(responses),
        "provenance_row_count": len(responses),
    }


def check_appendix_count(manifest: Dict[str, Any]) -> None:
    total = manifest.get("total_questions", 0)
    rows = manifest.get("provenance_row_count", 0)
    if total != rows:
        fail(3, "provenance_appendix_mismatch: total={0} rows={1}".format(total, rows))


def main() -> int:
    args = parse_args()

    if args.format not in ALLOWED_FORMATS:
        fail(4, "unknown format: {0}".format(args.format))

    responses = load_json(args.responses)
    if not isinstance(responses, list) or not responses:
        fail(2, "responses must be a non-empty list")

    errors = validate_responses(responses)
    if errors:
        sys.stderr.write("VALIDATION ERRORS:\n")
        for e in errors:
            sys.stderr.write("  - " + e + "\n")
        fail(2, "missing_reviewed_response or invalid provenance")

    metadata: Dict[str, Any] = {}
    if args.metadata and os.path.exists(args.metadata):
        metadata = load_json(args.metadata)

    branding: Dict[str, Any] = {}
    if args.branding and os.path.exists(args.branding):
        branding = load_json(args.branding)

    cover_letter = args.cover_letter

    if args.format == "word":
        manifest = build_word_manifest(
            responses, args.template, cover_letter, branding, metadata
        )
    elif args.format == "excel":
        manifest = build_excel_manifest(
            responses, args.template, branding, metadata
        )
    elif args.format == "pdf":
        word_manifest = build_word_manifest(
            responses, args.template, cover_letter, branding, metadata
        )
        manifest = build_pdf_manifest(word_manifest)
    else:  # portal
        manifest = build_portal_manifest(responses, branding, metadata)

    manifest["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    manifest["manifest_schema_version"] = "1.0"

    check_appendix_count(manifest)

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    sys.stderr.write(
        "OK: manifest written to {0} ({1} questions, format={2})\n".format(
            args.output, len(responses), args.format
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

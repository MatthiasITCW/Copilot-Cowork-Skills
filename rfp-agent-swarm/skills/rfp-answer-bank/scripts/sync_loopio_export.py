#!/usr/bin/env python3
"""
sync_loopio_export.py -- sync a Loopio CSV export into the local answer bank.

- Reads CSV using the stdlib `csv` module.
- Maps Loopio columns to bank schema (see references/loopio-sync-playbook.md).
- Diffs against current bank by `source_loopio_entry_id`.
- Applies adds and updates (version bump with history snapshot).
- Emits a list of deprecation candidates but does NOT auto-deprecate.
- Preserves entries whose current source=correction (correction-wins rule).
- Never hard-deletes.

Usage:
    python scripts/sync_loopio_export.py \
        --export-file path/to/loopio_export.csv \
        --bank-file working/bank.jsonl \
        --output working/sync_report.json
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

LOOPIO_CATEGORY_MAP = {
    "Security & Infosec": "security",
    "Privacy": "privacy",
    "Compliance & Certifications": "compliance",
    "Product Features": "product",
    "Integrations / APIs": "integrations",
    "Support & Ops": "operations",
    "Pricing & Commercial": "commercial",
    "Legal & Contracts": "legal",
    "Company Overview": "company",
    "Other / Misc": "other",
}

HTML_TAG_RE = re.compile(r"<[^>]+>")


def canonicalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_html(text: str) -> str:
    return HTML_TAG_RE.sub("", text or "").strip()


def parse_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw  # best-effort; reviewer will catch


def map_row(row: dict[str, str]) -> dict[str, Any] | None:
    status = (row.get("Status") or "").strip()
    if status and status.lower() != "published":
        return None

    loopio_id = (row.get("Entry ID") or "").strip()
    question = (row.get("Question") or "").strip()
    answer = strip_html(row.get("Answer") or "")
    if not loopio_id or not question or not answer:
        return None

    category_raw = (row.get("Category") or "").strip()
    category = LOOPIO_CATEGORY_MAP.get(category_raw, "other")

    tags = [t.strip().lower() for t in (row.get("Tags") or "").split(",") if t.strip()]
    certs = [c.strip().upper() for c in (row.get("Certifications") or "").split(",") if c.strip()]
    pricing = [p.strip() for p in (row.get("Pricing Ref") or "").split(",") if p.strip()]
    attachments = [a.strip() for a in (row.get("Attachments") or "").split("|") if a.strip()]

    return {
        "entry_id": str(uuid.uuid4()),  # placeholder; replaced if existing entry found
        "question_text": question,
        "canonical_question": canonicalize(question),
        "answer_text": answer,
        "category": category,
        "subcategory": "",
        "tags": tags,
        "source": "loopio_entry_id",
        "source_loopio_entry_id": loopio_id,
        "last_approved_date": parse_date(row.get("Last Reviewed") or ""),
        "approved_by": (row.get("Reviewed By") or "").strip(),
        "version": 1,
        "deprecated_flag": False,
        "replaces": [],
        "certifications_referenced": certs,
        "pricing_reference_ids": pricing,
        "evidence_attachments": attachments,
        "history": [],
    }


def load_bank(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            entries.append(json.loads(raw))
    return entries


def save_bank(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(path)


def index_by_loopio_id(bank: list[dict[str, Any]]) -> dict[str, int]:
    return {
        e.get("source_loopio_entry_id", ""): i
        for i, e in enumerate(bank)
        if e.get("source_loopio_entry_id")
    }


def apply_update(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    # correction-wins rule
    if existing.get("source") == "correction":
        return existing  # caller logs a conflict

    today_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    snapshot = {
        "version": existing.get("version", 1),
        "answer_text": existing.get("answer_text", ""),
        "last_approved_date": existing.get("last_approved_date", ""),
        "approved_by": existing.get("approved_by", ""),
        "retired_at": today_iso,
        "change_note": "loopio sync update",
    }
    history = list(existing.get("history", []))
    history.append(snapshot)

    merged = dict(existing)
    for key in (
        "question_text",
        "canonical_question",
        "answer_text",
        "category",
        "tags",
        "certifications_referenced",
        "pricing_reference_ids",
        "evidence_attachments",
        "last_approved_date",
        "approved_by",
    ):
        if incoming.get(key) not in (None, "", []):
            merged[key] = incoming[key]
    merged["source"] = "loopio_entry_id"
    merged["version"] = existing.get("version", 1) + 1
    merged["history"] = history
    return merged


def sync(
    export_path: Path,
    bank_path: Path,
    report_path: Path,
) -> None:
    bank = load_bank(bank_path)
    idx = index_by_loopio_id(bank)

    added: list[str] = []
    updated: list[str] = []
    conflicts: list[dict[str, Any]] = []
    deprecation_candidates: list[str] = []
    skipped_malformed = 0
    seen_loopio_ids: set[str] = set()

    try:
        fh = export_path.open("r", encoding="utf-8", newline="")
    except UnicodeDecodeError as err:
        print(f"[sync_loopio_export] ERROR opening export: {err}", file=sys.stderr)
        return

    with fh:
        reader = csv.DictReader(fh)
        for row_no, row in enumerate(reader, start=2):  # header is line 1
            incoming = map_row(row)
            if incoming is None:
                skipped_malformed += 1
                print(
                    f"[sync_loopio_export] WARN: skipping row {row_no} (malformed or non-published)",
                    file=sys.stderr,
                )
                continue
            loopio_id = incoming["source_loopio_entry_id"]
            seen_loopio_ids.add(loopio_id)

            if loopio_id in idx:
                pos = idx[loopio_id]
                existing = bank[pos]
                if existing.get("source") == "correction":
                    conflicts.append(
                        {
                            "loopio_entry_id": loopio_id,
                            "entry_id": existing.get("entry_id"),
                            "why": "bank version came from correction; correction wins",
                        }
                    )
                    continue
                if (
                    existing.get("answer_text") == incoming["answer_text"]
                    and existing.get("category") == incoming["category"]
                ):
                    continue  # no-op
                bank[pos] = apply_update(existing, incoming)
                updated.append(existing.get("entry_id", ""))
            else:
                # keep the placeholder UUID as the new entry_id
                bank.append(incoming)
                added.append(incoming["entry_id"])

    # Deprecation candidates = bank entries whose source was loopio but are missing from export
    for entry in bank:
        if (
            entry.get("source") == "loopio_entry_id"
            and entry.get("source_loopio_entry_id")
            and entry["source_loopio_entry_id"] not in seen_loopio_ids
            and not entry.get("deprecated_flag", False)
        ):
            deprecation_candidates.append(entry["entry_id"])

    save_bank(bank_path, bank)

    report = {
        "synced_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "export_file": str(export_path),
        "added_count": len(added),
        "updated_count": len(updated),
        "conflicts": conflicts,
        "deprecation_candidates": deprecation_candidates,
        "skipped_malformed": skipped_malformed,
        "added_entry_ids": added,
        "updated_entry_ids": updated,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"[sync_loopio_export] added={len(added)} updated={len(updated)} "
        f"conflicts={len(conflicts)} dep_candidates={len(deprecation_candidates)}",
        file=sys.stderr,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Loopio CSV export into answer bank")
    ap.add_argument("--export-file", required=True)
    ap.add_argument("--bank-file", default="working/bank.jsonl")
    ap.add_argument("--output", default="working/sync_report.json")
    args = ap.parse_args()

    export_path = Path(args.export_file)
    bank_path = Path(args.bank_file)
    report_path = Path(args.output)

    if not export_path.exists():
        print(
            f"[sync_loopio_export] ERROR: export file not found: {export_path}",
            file=sys.stderr,
        )
        return 2

    sync(export_path, bank_path, report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
add_entry.py -- add or update a single answer-bank entry.

- Generates UUID4 entry_id on insert.
- On update (entry_id passed), bumps version and preserves prior version in history[].
- Refuses to write without approved_by for source in {internal_sme, correction}.
- Writes JSONL (one entry per line) to --bank-file.

Usage (insert):
    python scripts/add_entry.py \
        --question "Do you support SAML 2.0 SSO?" \
        --answer "Yes. Contoso supports SAML 2.0 via Okta, Azure AD, Ping..." \
        --category integrations \
        --source internal_sme \
        --approved-by secops@contoso.com \
        --tags saml,sso,idp \
        --bank-file working/bank.jsonl

Usage (update):
    python scripts/add_entry.py \
        --entry-id b1b2a0c4-2c9f-4f52-9f14-6ab5df3d1e2a \
        --answer "Yes. Expanded answer..." \
        --approved-by secops@contoso.com \
        --change-note "Added SCIM detail" \
        --bank-file working/bank.jsonl
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

ALLOWED_CATEGORIES = {
    "security", "privacy", "compliance", "product",
    "integrations", "operations", "commercial", "legal",
    "company", "other",
}
ALLOWED_SOURCES = {"loopio_entry_id", "internal_sme", "correction"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def canonicalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


def require(condition: bool, msg: str) -> None:
    if not condition:
        print(f"[add_entry] ERROR: {msg}", file=sys.stderr)
        raise SystemExit(2)


def new_entry(args: argparse.Namespace) -> dict[str, Any]:
    require(bool(args.question), "--question is required on insert")
    require(bool(args.answer), "--answer is required on insert")
    require(args.category in ALLOWED_CATEGORIES, f"--category must be one of {sorted(ALLOWED_CATEGORIES)}")
    require(args.source in ALLOWED_SOURCES, f"--source must be one of {sorted(ALLOWED_SOURCES)}")

    if args.source in {"internal_sme", "correction"}:
        require(bool(args.approved_by), f"--approved-by required when source={args.source}")
        require(bool(EMAIL_RE.match(args.approved_by or "")), "--approved-by must be an email")

    tags = [t.strip().lower() for t in (args.tags or "").split(",") if t.strip()]
    certs = [c.strip().upper() for c in (args.certifications or "").split(",") if c.strip()]
    pricing = [p.strip() for p in (args.pricing_refs or "").split(",") if p.strip()]
    attachments = [a.strip() for a in (args.attachments or "").split(",") if a.strip()]

    today = dt.date.today().isoformat()
    entry = {
        "entry_id": str(uuid.uuid4()),
        "question_text": args.question,
        "canonical_question": canonicalize(args.question),
        "answer_text": args.answer,
        "category": args.category,
        "subcategory": args.subcategory or "",
        "tags": tags,
        "source": args.source,
        "source_loopio_entry_id": args.loopio_entry_id or "",
        "last_approved_date": args.approved_date or today,
        "approved_by": args.approved_by or "",
        "version": 1,
        "deprecated_flag": False,
        "replaces": [],
        "certifications_referenced": certs,
        "pricing_reference_ids": pricing,
        "evidence_attachments": attachments,
        "history": [],
    }
    return entry


def update_entry(existing: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    require(bool(args.approved_by), "--approved-by is required on update")
    require(bool(EMAIL_RE.match(args.approved_by or "")), "--approved-by must be an email")

    today_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    snapshot = {
        "version": existing.get("version", 1),
        "answer_text": existing.get("answer_text", ""),
        "last_approved_date": existing.get("last_approved_date", ""),
        "approved_by": existing.get("approved_by", ""),
        "retired_at": today_iso,
        "change_note": args.change_note or "",
    }
    history = list(existing.get("history", []))
    history.append(snapshot)

    if args.answer:
        existing["answer_text"] = args.answer
    if args.question:
        existing["question_text"] = args.question
        existing["canonical_question"] = canonicalize(args.question)
    if args.category:
        require(
            args.category in ALLOWED_CATEGORIES,
            f"--category must be one of {sorted(ALLOWED_CATEGORIES)}",
        )
        existing["category"] = args.category
    if args.subcategory is not None:
        existing["subcategory"] = args.subcategory
    if args.tags is not None:
        existing["tags"] = [t.strip().lower() for t in args.tags.split(",") if t.strip()]

    existing["version"] = existing.get("version", 1) + 1
    existing["last_approved_date"] = (
        args.approved_date or dt.date.today().isoformat()
    )
    existing["approved_by"] = args.approved_by
    existing["history"] = history
    return existing


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Add or update an answer-bank entry")
    ap.add_argument("--entry-id", help="If set, update this entry")
    ap.add_argument("--question")
    ap.add_argument("--answer")
    ap.add_argument("--category")
    ap.add_argument("--subcategory", default=None)
    ap.add_argument("--source", default="internal_sme")
    ap.add_argument("--approved-by")
    ap.add_argument("--approved-date", help="ISO date; defaults to today")
    ap.add_argument("--tags", help="Comma-separated")
    ap.add_argument("--certifications", help="Comma-separated; uppercased")
    ap.add_argument("--pricing-refs", help="Comma-separated")
    ap.add_argument("--attachments", help="Comma-separated URLs")
    ap.add_argument("--loopio-entry-id", help="Stable Loopio ID")
    ap.add_argument("--change-note", help="Required-ish on update")
    ap.add_argument("--bank-file", default="working/bank.jsonl")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    bank_path = Path(args.bank_file)
    bank = load_bank(bank_path)

    if args.entry_id:
        # Update path
        for i, entry in enumerate(bank):
            if entry.get("entry_id") == args.entry_id:
                bank[i] = update_entry(entry, args)
                save_bank(bank_path, bank)
                print(
                    json.dumps(
                        {
                            "operation": "update",
                            "entry_id": args.entry_id,
                            "version": bank[i]["version"],
                        }
                    )
                )
                return 0
        print(
            f"[add_entry] ERROR: entry_id {args.entry_id} not found in {bank_path}",
            file=sys.stderr,
        )
        return 2

    # Insert path
    entry = new_entry(args)
    bank.append(entry)
    save_bank(bank_path, bank)
    print(
        json.dumps(
            {
                "operation": "insert",
                "entry_id": entry["entry_id"],
                "version": entry["version"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
merge_corrections.py -- apply reviewer corrections from rfp-review into the bank.

Implements the per-reason rules in references/corrections-merge-rules.md.

- Refuses to apply any correction missing reviewed_by / reviewed_at / sign_off_token.
- Idempotent: maintains working/bank.applied.json (applied correction_ids).
- Never hard-deletes. POLICY_UPDATE sets deprecated_flag=true and adds successor.
- Writes merge_report.json keyed by reason.

Usage:
    python scripts/merge_corrections.py \
        --corrections working/corrections.jsonl \
        --bank-file working/bank.jsonl \
        --output working/merge_report.json
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

REASONS = {
    "FACTUAL_ERROR",
    "OUTDATED_SOURCE",
    "TONE_OR_STYLE",
    "MISSING_CONTEXT",
    "CATEGORY_MISCLASSIFICATION",
    "UNANSWERABLE_FROM_KB",
    "POLICY_UPDATE",
    "COMPLIANCE_NUANCE",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STALENESS_DAYS = 90


def canonicalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError as err:
                print(
                    f"[merge_corrections] WARN line {line_no}: {err}",
                    file=sys.stderr,
                )
    return out


def save_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tmp.replace(path)


def load_applied(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("applied_correction_ids", []))
    except Exception:
        return set()


def save_applied(path: Path, ids: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"applied_correction_ids": sorted(ids)}, indent=2),
        encoding="utf-8",
    )


def find_entry(bank: list[dict[str, Any]], entry_id: str) -> int:
    for i, e in enumerate(bank):
        if e.get("entry_id") == entry_id:
            return i
    return -1


def snapshot(existing: dict[str, Any], change_note: str) -> dict[str, Any]:
    return {
        "version": existing.get("version", 1),
        "answer_text": existing.get("answer_text", ""),
        "last_approved_date": existing.get("last_approved_date", ""),
        "approved_by": existing.get("approved_by", ""),
        "retired_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "change_note": change_note,
    }


def verify_signoff(correction: dict[str, Any]) -> str | None:
    if not correction.get("reviewed_by"):
        return "missing reviewed_by"
    if not EMAIL_RE.match(correction["reviewed_by"]):
        return "reviewed_by not a valid email"
    if not correction.get("reviewed_at"):
        return "missing reviewed_at"
    if not correction.get("sign_off_token"):
        return "missing sign_off_token"
    try:
        reviewed = dt.datetime.fromisoformat(
            correction["reviewed_at"].replace("Z", "+00:00")
        )
    except ValueError:
        return "reviewed_at not ISO-8601"
    age = dt.datetime.now(dt.timezone.utc) - reviewed
    if age.days > STALENESS_DAYS:
        return f"reviewed_at older than {STALENESS_DAYS} days"
    return None


def apply_factual_or_outdated(
    bank: list[dict[str, Any]],
    correction: dict[str, Any],
    change_note: str,
) -> tuple[bool, str]:
    idx = find_entry(bank, correction.get("target_entry_id", ""))
    if idx < 0:
        return False, "target not found"
    existing = bank[idx]
    if existing.get("deprecated_flag"):
        return False, "target deprecated"
    history = list(existing.get("history", []))
    history.append(snapshot(existing, change_note))
    reviewed_at = correction["reviewed_at"]
    approved_date = reviewed_at.split("T")[0] if "T" in reviewed_at else reviewed_at
    existing["answer_text"] = correction.get("corrected_answer", existing["answer_text"])
    existing["version"] = existing.get("version", 1) + 1
    existing["last_approved_date"] = approved_date
    existing["approved_by"] = correction["reviewed_by"]
    existing["source"] = "correction"
    existing["history"] = history
    bank[idx] = existing
    return True, existing["entry_id"]


def apply_retag(
    bank: list[dict[str, Any]],
    correction: dict[str, Any],
) -> tuple[bool, str]:
    idx = find_entry(bank, correction.get("target_entry_id", ""))
    if idx < 0:
        return False, "target not found"
    try:
        payload = json.loads(correction.get("corrected_answer", "{}"))
    except json.JSONDecodeError:
        return False, "retag payload not JSON"
    existing = bank[idx]
    history = list(existing.get("history", []))
    old_cat = existing.get("category")
    history.append(snapshot(existing, f"retag: {old_cat} -> {payload.get('category', old_cat)}"))
    if "category" in payload:
        existing["category"] = payload["category"]
    if "subcategory" in payload:
        existing["subcategory"] = payload["subcategory"]
    if "tags" in payload:
        existing["tags"] = [t.lower() for t in payload["tags"]]
    existing["version"] = existing.get("version", 1) + 1
    existing["history"] = history
    bank[idx] = existing
    return True, existing["entry_id"]


def make_new_entry(
    correction: dict[str, Any],
    category: str,
    extra_tags: list[str],
    source: str,
) -> dict[str, Any]:
    q = correction.get("question_text", "")
    reviewed_at = correction["reviewed_at"]
    approved_date = reviewed_at.split("T")[0] if "T" in reviewed_at else reviewed_at
    return {
        "entry_id": str(uuid.uuid4()),
        "question_text": q,
        "canonical_question": canonicalize(q),
        "answer_text": correction.get("corrected_answer", ""),
        "category": category,
        "subcategory": "",
        "tags": extra_tags,
        "source": source,
        "source_loopio_entry_id": "",
        "last_approved_date": approved_date,
        "approved_by": correction["reviewed_by"],
        "version": 1,
        "deprecated_flag": False,
        "replaces": [],
        "certifications_referenced": [],
        "pricing_reference_ids": [],
        "evidence_attachments": [],
        "history": [],
    }


def merge(
    corrections: list[dict[str, Any]],
    bank: list[dict[str, Any]],
    already_applied: set[str],
) -> dict[str, Any]:
    applied_by_reason: dict[str, int] = {r: 0 for r in REASONS}
    skipped: list[dict[str, Any]] = []
    skipped_duplicates: list[str] = []
    conflicts: list[dict[str, Any]] = []
    affected: set[str] = set()

    # Sort by reviewed_at for deterministic layering
    corrections_sorted = sorted(
        corrections, key=lambda c: c.get("reviewed_at", "")
    )

    for corr in corrections_sorted:
        cid = corr.get("correction_id", "")
        if not cid:
            conflicts.append({"correction_id": "<missing>", "why": "no correction_id"})
            continue
        if cid in already_applied:
            skipped_duplicates.append(cid)
            continue

        why = verify_signoff(corr)
        if why:
            conflicts.append({"correction_id": cid, "why": why})
            continue

        reason = corr.get("reason", "")
        if reason not in REASONS:
            conflicts.append({"correction_id": cid, "why": f"unknown reason {reason}"})
            continue

        if reason == "TONE_OR_STYLE":
            skipped.append({"correction_id": cid, "reason_code": reason})
            already_applied.add(cid)
            continue

        if reason in ("FACTUAL_ERROR", "OUTDATED_SOURCE"):
            ok, info = apply_factual_or_outdated(
                bank,
                corr,
                change_note=f"correction_id={cid}: {corr.get('reviewer_notes', '')}",
            )
            if ok:
                applied_by_reason[reason] += 1
                affected.add(info)
                already_applied.add(cid)
            else:
                conflicts.append({"correction_id": cid, "why": info})

        elif reason == "CATEGORY_MISCLASSIFICATION":
            ok, info = apply_retag(bank, corr)
            if ok:
                applied_by_reason[reason] += 1
                affected.add(info)
                already_applied.add(cid)
            else:
                conflicts.append({"correction_id": cid, "why": info})

        elif reason == "MISSING_CONTEXT":
            # Inherit category from target if present
            idx = find_entry(bank, corr.get("target_entry_id", ""))
            category = bank[idx]["category"] if idx >= 0 else "other"
            new = make_new_entry(
                corr,
                category=category,
                extra_tags=[f"context:{corr.get('rfp_id', 'unknown')}"],
                source="correction",
            )
            bank.append(new)
            applied_by_reason[reason] += 1
            affected.add(new["entry_id"])
            already_applied.add(cid)

        elif reason == "UNANSWERABLE_FROM_KB":
            new = make_new_entry(
                corr,
                category="other",
                extra_tags=["origin:rfp-review"],
                source="internal_sme",
            )
            bank.append(new)
            applied_by_reason[reason] += 1
            affected.add(new["entry_id"])
            already_applied.add(cid)

        elif reason == "POLICY_UPDATE":
            idx = find_entry(bank, corr.get("target_entry_id", ""))
            if idx < 0:
                conflicts.append({"correction_id": cid, "why": "target not found"})
                continue
            existing = bank[idx]
            history = list(existing.get("history", []))
            history.append(snapshot(existing, f"superseded by correction {cid}"))
            existing["history"] = history
            existing["deprecated_flag"] = True
            bank[idx] = existing
            new = make_new_entry(
                corr,
                category=existing.get("category", "other"),
                extra_tags=existing.get("tags", []),
                source="correction",
            )
            new["replaces"] = [existing["entry_id"]]
            bank.append(new)
            applied_by_reason[reason] += 1
            affected.update([existing["entry_id"], new["entry_id"]])
            already_applied.add(cid)

        elif reason == "COMPLIANCE_NUANCE":
            juris = corr.get("jurisdiction", "other")
            idx = find_entry(bank, corr.get("target_entry_id", ""))
            category = bank[idx]["category"] if idx >= 0 else "compliance"
            base_tags = bank[idx].get("tags", []) if idx >= 0 else []
            new = make_new_entry(
                corr,
                category=category,
                extra_tags=list(base_tags) + [f"jurisdiction:{juris}"],
                source="correction",
            )
            bank.append(new)
            applied_by_reason[reason] += 1
            affected.add(new["entry_id"])
            already_applied.add(cid)

    return {
        "merged_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_input": len(corrections),
        "applied_by_reason": applied_by_reason,
        "skipped": skipped,
        "skipped_duplicates": skipped_duplicates,
        "conflicts": conflicts,
        "affected_entry_ids": sorted(affected),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge rfp-review corrections into the bank")
    ap.add_argument("--corrections", required=True)
    ap.add_argument("--bank-file", default="working/bank.jsonl")
    ap.add_argument("--output", default="working/merge_report.json")
    ap.add_argument("--applied-file", default="working/bank.applied.json")
    args = ap.parse_args()

    corrections_path = Path(args.corrections)
    bank_path = Path(args.bank_file)
    report_path = Path(args.output)
    applied_path = Path(args.applied_file)

    if not corrections_path.exists():
        print(
            f"[merge_corrections] ERROR corrections file not found: {corrections_path}",
            file=sys.stderr,
        )
        return 2

    corrections = load_jsonl(corrections_path)
    bank = load_jsonl(bank_path)
    already_applied = load_applied(applied_path)

    report = merge(corrections, bank, already_applied)

    save_jsonl(bank_path, bank)
    save_applied(applied_path, already_applied)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"[merge_corrections] applied={sum(report['applied_by_reason'].values())} "
        f"skipped={len(report['skipped'])} "
        f"duplicates={len(report['skipped_duplicates'])} "
        f"conflicts={len(report['conflicts'])}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
parse_rfp.py — Stage 1 of the rfp-intake pipeline.

Reads a plain-text or simple-CSV extraction of an RFP (produced upstream by
the docx / xlsx / pdf built-in skills) and emits a structured JSON record:

    {
      "rfp_id": "...",
      "buyer": "...",
      "rfp_title": "...",
      "response_deadline": "...",
      "deadline_candidates": [...],
      "submission_format": "...",
      "sections": [...],
      "raw_questions": [
          { "question_id": "Q-0001", "section": "...", "text": "...", "source_line": 42 },
          ...
      ],
      "parse_confidence": "HIGH" | "MEDIUM" | "LOW",
      "parsed_at": "...",
      "source_documents": ["..."],
      "parse_log": [...]
    }

Python 3 stdlib only. Non-zero exit on fatal errors; human-readable errors
go to stderr. Idempotent — same input produces the same output.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
from typing import Any


QUESTION_STEMS = (
    "describe", "explain", "provide", "confirm", "list", "how does",
    "how do", "what is", "what are", "does your", "do you", "can you",
    "is your", "are your", "please describe", "please explain",
    "please provide", "detail", "outline",
)

NUMBERED_Q_RE = re.compile(r"^\s*(?:Q|Question)\s*\d+[\.\):\-]?\s+", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s*\d+(?:\.\d+){0,3}\s+\S")
BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[\.\)])\s+\S")
DEADLINE_RE = re.compile(
    r"(?:deadline|due|closing\s+date|submission\s+deadline|response\s+due|must\s+be\s+received\s+by)"
    r"[^\n]{0,80}?(\d{1,2}[\s/\-][A-Za-z]{3,9}[\s/\-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
BUYER_RE = re.compile(
    r"(?:issued\s+by|prepared\s+by|submitted\s+to|from)\s*[:\-]?\s*([A-Z][A-Za-z0-9&\.\- ,]{2,80})"
)
SUBMISSION_HINTS = {
    "portal": ("via portal", "upload to", "through our portal", "via the sourcing portal"),
    "email": ("email to", "submit by email", "submit via email"),
    "file_upload": ("upload", "sharepoint", "box.com", "dropbox"),
    "physical": ("hand deliver", "courier", "by mail"),
}


def looks_like_question(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    lower = stripped.lower()
    if any(lower.startswith(stem) for stem in QUESTION_STEMS):
        return True
    if NUMBERED_Q_RE.match(stripped):
        return True
    return False


def read_input(path: str) -> tuple[list[str], str]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".tsv"):
        return read_delimited(path, ext), ext
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines(), ext


def read_delimited(path: str, ext: str) -> list[str]:
    delim = "\t" if ext == ".tsv" else ","
    out: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh, delimiter=delim)
        header: list[str] | None = None
        for row in reader:
            if header is None:
                header = [c.strip().lower() for c in row]
                continue
            if not any(c.strip() for c in row):
                continue
            # Choose the text-like column
            text = ""
            for idx, col in enumerate(header):
                if col in ("question", "question text", "requirement", "control",
                           "description", "text", "item"):
                    if idx < len(row):
                        text = row[idx].strip()
                        break
            if not text:
                text = " | ".join(c.strip() for c in row if c.strip())
            if text:
                out.append(text)
    return out


def detect_sections_and_questions(
    lines: list[str], id_prefix: str
) -> tuple[list[str], list[dict[str, Any]]]:
    sections: list[str] = []
    current_section = ""
    questions: list[dict[str, Any]] = []
    counter = 0
    in_q_block = False

    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if not line.strip():
            continue
        # Heading detection
        if HEADING_RE.match(line) and not looks_like_question(line):
            current_section = line.strip()
            if current_section not in sections:
                sections.append(current_section)
            lower = current_section.lower()
            in_q_block = any(
                marker in lower for marker in ("questions", "requirements", "questionnaire")
            )
            continue
        # Question detection
        is_q = looks_like_question(line)
        if not is_q and in_q_block and BULLET_RE.match(line):
            is_q = True
        if is_q:
            counter += 1
            qid = f"{id_prefix}-{counter:04d}"
            questions.append(
                {
                    "question_id": qid,
                    "section": current_section,
                    "text": line.strip(),
                    "source_line": idx,
                }
            )
    return sections, questions


def extract_buyer(text: str) -> str:
    m = BUYER_RE.search(text)
    if m:
        return m.group(1).strip().rstrip(",.")
    return ""


def extract_deadline_candidates(text: str) -> list[str]:
    return [m.group(1).strip() for m in DEADLINE_RE.finditer(text)]


def extract_submission_format(text: str) -> str:
    lower = text.lower()
    for fmt, hints in SUBMISSION_HINTS.items():
        for hint in hints:
            if hint in lower:
                return fmt
    return ""


def normalise_deadline(candidate: str) -> str | None:
    candidate = candidate.strip()
    fmts = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %B %Y", "%d %b %Y",
            "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%y", "%m/%d/%y")
    for fmt in fmts:
        try:
            parsed = dt.datetime.strptime(candidate, fmt)
            return parsed.date().isoformat()
        except ValueError:
            continue
    return None


def generate_rfp_id(source: str, now: dt.datetime) -> str:
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:4].upper()
    return f"RFP-{now.year:04d}-{digest}"


def score_confidence(
    questions: list[dict[str, Any]],
    deadline: str | None,
    buyer: str,
    source_ext: str,
) -> tuple[str, list[str]]:
    log: list[str] = []
    if not questions:
        log.append("no questions detected")
        return "LOW", log
    missing_text = sum(1 for q in questions if not q["text"])
    if missing_text:
        log.append(f"{missing_text} questions with empty text")
    band = "HIGH"
    if not deadline:
        log.append("no deadline extracted")
        band = "MEDIUM"
    if not buyer:
        log.append("no buyer extracted")
        band = "MEDIUM"
    if source_ext == ".pdf":
        log.append("pdf source — capping at MEDIUM unless text-layer verified")
        band = "MEDIUM" if band == "HIGH" else band
    return band, log


def build_output(
    input_path: str,
    lines: list[str],
    source_ext: str,
) -> dict[str, Any]:
    full_text = "\n".join(lines)
    now = dt.datetime.now(dt.timezone.utc)
    rfp_id = generate_rfp_id(input_path + full_text[:512], now)
    buyer = extract_buyer(full_text)
    raw_deadlines = extract_deadline_candidates(full_text)
    normalised = [d for d in (normalise_deadline(c) for c in raw_deadlines) if d]
    deadline = normalised[0] if normalised else None
    sections, questions = detect_sections_and_questions(lines, "Q")
    confidence, log = score_confidence(questions, deadline, buyer, source_ext)
    return {
        "rfp_id": rfp_id,
        "buyer": buyer,
        "rfp_title": "",
        "response_deadline": deadline,
        "deadline_candidates": raw_deadlines,
        "submission_format": extract_submission_format(full_text),
        "sections": sections,
        "raw_questions": questions,
        "parse_confidence": confidence,
        "parsed_at": now.isoformat(),
        "source_documents": [input_path],
        "parse_log": log,
    }


def merge_append(existing: dict[str, Any], addition: dict[str, Any]) -> dict[str, Any]:
    existing["source_documents"] = list(
        dict.fromkeys(existing.get("source_documents", []) + addition.get("source_documents", []))
    )
    existing["sections"] = list(
        dict.fromkeys(existing.get("sections", []) + addition.get("sections", []))
    )
    base = len(existing.get("raw_questions", []))
    for i, q in enumerate(addition.get("raw_questions", []), start=1):
        q = dict(q)
        q["question_id"] = f"Q-{base + i:04d}"
        existing["raw_questions"].append(q)
    existing["parse_log"] = existing.get("parse_log", []) + addition.get("parse_log", [])
    if existing.get("parse_confidence") != addition.get("parse_confidence"):
        ranks = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        existing["parse_confidence"] = min(
            (existing.get("parse_confidence", "HIGH"), addition.get("parse_confidence", "HIGH")),
            key=lambda b: ranks.get(b, 0),
        )
    return existing


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Parse an extracted RFP text file into rfp_raw.json")
    ap.add_argument("input_path", help="Path to extracted .txt / .md / .csv / .tsv")
    ap.add_argument("--output", required=True, help="Path to write rfp_raw.json")
    ap.add_argument("--append", action="store_true", help="Merge into existing output if present")
    ap.add_argument("--id-column", help="CSV/TSV: name of ID column", default=None)
    ap.add_argument("--text-column", help="CSV/TSV: name of text column", default=None)
    args = ap.parse_args(argv)

    try:
        if not os.path.isfile(args.input_path):
            print(f"ERROR: input not found: {args.input_path}", file=sys.stderr)
            return 1
        lines, ext = read_input(args.input_path)
        new_record = build_output(args.input_path, lines, ext)
        if args.append and os.path.isfile(args.output):
            with open(args.output, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
            merged = merge_append(existing, new_record)
            out = merged
        else:
            out = new_record
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
        print(json.dumps({
            "ok": True,
            "rfp_id": out["rfp_id"],
            "questions": len(out["raw_questions"]),
            "confidence": out["parse_confidence"],
            "output": args.output,
        }))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: parse failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

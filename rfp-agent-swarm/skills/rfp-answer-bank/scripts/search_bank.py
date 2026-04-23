#!/usr/bin/env python3
"""
search_bank.py -- hybrid-search the RFP answer bank.

POC implementation: reads a local JSONL bank file and runs a stdlib-only
approximation of BM25 + a Jaccard "vector" proxy + a blended "rerank" score.
The contract at the CLI / JSON boundary matches what the production Azure
AI Search-backed version will expose, so downstream skills (rfp-respond,
rfp-fit-assessment, rfp-assemble) can develop against this offline.

Production note: the real implementation will POST to the Azure AI Search
`/docs/search.post.search` endpoint with vectorQueries + semantic config.
The tiering logic below is intentionally shared.

Usage:
    python scripts/search_bank.py \
        --query "do you support SAML SSO" \
        --category integrations \
        --top-k 5 \
        --bank-file working/bank.jsonl \
        --output working/search_result.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# ---------- Config ----------

SYNONYM_MAP: dict[str, list[str]] = {
    "sso": ["single sign-on", "single signon", "sign on"],
    "mfa": ["multi-factor authentication", "multi factor auth", "two-factor", "2fa"],
    "dpa": ["data processing agreement", "data processing addendum"],
    "soc2": ["soc 2", "service organization control 2"],
    "gdpr": ["general data protection regulation"],
    "ccpa": ["california consumer privacy act"],
    "sla": ["service level agreement", "uptime commitment"],
    "scim": ["system for cross-domain identity management", "provisioning"],
    "idp": ["identity provider"],
    "rto": ["recovery time objective"],
    "rpo": ["recovery point objective"],
    "pii": ["personally identifiable information"],
}

TIER_HIGH = 0.90
TIER_MEDIUM = 0.75

BM25_K1 = 1.5
BM25_B = 0.75

TOKEN_RE = re.compile(r"[a-z0-9]+")


# ---------- Helpers ----------

def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def expand_query(query: str) -> str:
    tokens = tokenize(query)
    expanded: list[str] = list(tokens)
    for tok in tokens:
        if tok in SYNONYM_MAP:
            for syn in SYNONYM_MAP[tok]:
                expanded.extend(tokenize(syn))
        for canonical, syns in SYNONYM_MAP.items():
            for syn in syns:
                if tok in tokenize(syn):
                    expanded.append(canonical)
    return " ".join(expanded)


def load_bank(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError as err:
                print(
                    f"[search_bank] WARN: skipping malformed line {line_no}: {err}",
                    file=sys.stderr,
                )
    return entries


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avgdl: float,
    df: dict[str, int],
    n_docs: int,
) -> float:
    if not doc_tokens:
        return 0.0
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    score = 0.0
    for qt in set(query_tokens):
        if qt not in tf:
            continue
        idf = math.log(1 + (n_docs - df.get(qt, 0) + 0.5) / (df.get(qt, 0) + 0.5))
        num = tf[qt] * (BM25_K1 + 1)
        denom = tf[qt] + BM25_K1 * (1 - BM25_B + BM25_B * dl / avgdl)
        score += idf * (num / denom)
    return score


def trigrams(tokens: list[str]) -> set[str]:
    joined = " ".join(tokens)
    return {joined[i : i + 3] for i in range(max(0, len(joined) - 2))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def tier_for(score: float) -> str:
    if score >= TIER_HIGH:
        return "HIGH"
    if score >= TIER_MEDIUM:
        return "MEDIUM"
    return "LOW"


# ---------- Core search ----------

def search(
    query: str,
    bank: list[dict[str, Any]],
    category: str | None,
    top_k: int,
    include_deprecated: bool,
) -> list[dict[str, Any]]:
    active = [
        e for e in bank
        if include_deprecated or not e.get("deprecated_flag", False)
    ]
    if category:
        active = [e for e in active if e.get("category") == category]

    if not active:
        return []

    expanded = expand_query(query)
    q_tokens = tokenize(expanded)
    q_trigrams = trigrams(q_tokens)

    # Build doc tokens
    docs: list[list[str]] = []
    for e in active:
        body = " ".join(
            [
                str(e.get("canonical_question", "")),
                str(e.get("question_text", "")),
                str(e.get("answer_text", "")),
                " ".join(e.get("tags", []) or []),
            ]
        )
        docs.append(tokenize(body))

    # Document frequency
    df: dict[str, int] = {}
    for toks in docs:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / n_docs if n_docs else 1.0

    # Compute scores
    bm25s = [bm25_score(q_tokens, d, avgdl, df, n_docs) for d in docs]
    bm25_max = max(bm25s) if bm25s else 1.0
    bm25_norm = [s / bm25_max if bm25_max > 0 else 0.0 for s in bm25s]

    jacs = [jaccard(q_trigrams, trigrams(d)) for d in docs]

    rerank = [0.7 * b + 0.3 * j for b, j in zip(bm25_norm, jacs)]

    # Build result list
    results: list[dict[str, Any]] = []
    for entry, b, v, r in zip(active, bm25_norm, jacs, rerank):
        results.append(
            {
                "entry_id": entry.get("entry_id"),
                "question_text": entry.get("question_text"),
                "answer_text": entry.get("answer_text"),
                "category": entry.get("category"),
                "tags": entry.get("tags", []),
                "source": entry.get("source"),
                "last_approved_date": entry.get("last_approved_date"),
                "version": entry.get("version"),
                "bm25_score": round(b, 4),
                "vector_score": round(v, 4),
                "rerank_score": round(r, 4),
                "tier": tier_for(r),
            }
        )

    results.sort(key=lambda x: x["rerank_score"], reverse=True)
    return results[:top_k]


# ---------- CLI ----------

def main() -> int:
    ap = argparse.ArgumentParser(description="Search the RFP answer bank (POC)")
    ap.add_argument("--query", required=True, help="Query text")
    ap.add_argument("--category", default=None, help="Optional category filter")
    ap.add_argument("--top-k", type=int, default=5, help="Top results to return")
    ap.add_argument(
        "--bank-file",
        default="working/bank.jsonl",
        help="Local bank JSONL file",
    )
    ap.add_argument(
        "--output",
        default="working/search_result.json",
        help="Destination JSON file",
    )
    ap.add_argument(
        "--include-deprecated",
        action="store_true",
        help="Include deprecated entries (never set in production callers)",
    )
    args = ap.parse_args()

    bank_path = Path(args.bank_file)
    bank = load_bank(bank_path)
    results = search(
        query=args.query,
        bank=bank,
        category=args.category,
        top_k=args.top_k,
        include_deprecated=args.include_deprecated,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": args.query,
        "expanded_query": expand_query(args.query),
        "category": args.category,
        "top_k": args.top_k,
        "results": results,
        "bank_entry_count": len(bank),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"[search_bank] {len(results)} result(s) written to {out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

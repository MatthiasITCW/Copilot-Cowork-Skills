# Confidence Tier Rules

The authoritative reference for how `rfp-respond` assigns a tier and a 0–100 confidence score to every response. Implemented by `scripts/confidence_scorer.py`; cross-checked by `rfp-gates`.

## 1. Tier Definitions

| Tier | Reranker score band | Meaning | Default review path |
|---|---|---|---|
| HIGH | ≥ 0.90 | KB-matched, exact or near-exact reuse | Light verification (spot-check) |
| MEDIUM | 0.75 – 0.89 | KB-adapted from a related, approved entry | Standard review; reviewer verifies the delta |
| LOW | < 0.75 | No strong match; AI-generated with caveats | Mandatory SME review before submission |

The reranker score is the **semantic reranker score** emitted by Azure AI Search, not the raw BM25 or vector similarity. Raw signals are inputs to the reranker, not to the tier decision.

## 2. Confidence Score Formula

The tier is categorical; the 0–100 confidence is continuous and is used for sorting reviewer queues and for the progress card.

```
base = reranker_score * 100                # 0..100

adjustments (additive, bounded):
  + category_match_bonus            up to +5   if the bank entry's category tag matches the question's tag
  + freshness_bonus                 up to +3   if last_approved_date within 6 months
  - staleness_penalty               up to -6   if last_approved_date older than 18 months
  + length_similarity_bonus         up to +2   if question length is within 30% of bank question length
  - framework_mismatch_penalty      -10        if question names a framework (SOC 2, ISO 27001, GDPR) that the source entry does not

confidence = clamp(base + adjustments, 0, 100)
```

### Capping rule (non-negotiable)

If the final response text was **generated** (tier LOW) rather than retrieved, confidence is clamped to a ceiling of **75**, no matter what the formula returns. Capping happens last, after all adjustments.

```
if source == "GENERATED":
    confidence = min(confidence, 75)
```

This is enforced in code and re-checked by `rfp-gates`. Any row where `source == "GENERATED"` and `confidence > 75` is treated as a pipeline bug and the run fails.

## 3. Provenance Requirements

Every response row must carry provenance. Requirements vary by tier:

| Field | HIGH | MEDIUM | LOW |
|---|---|---|---|
| `bank_entry_id` | Required | Required (or list of IDs if stitched) | `"GENERATED"` or `"GENERATED+<id>"` if a weak seed was used |
| `last_approved_date` | Required (ISO 8601) | Required | `null` for pure generation, else source date |
| `original_question` | Required verbatim | Required verbatim | Optional |
| `delta_summary` | Must be empty | Required, ≤160 chars | Required if a seed entry was adapted |
| `adapted_question` | N/A | Optional, for audit | N/A |
| `generation_seed` | N/A | N/A | Required for LOW: brief description of what the generator was given |

Missing provenance is a hard fail in `rfp-gates`.

## 4. Tier Override Policy

Only two parties may change a tier after `confidence_scorer.py` assigns it:

| Actor | Can promote? | Can demote? | Mechanism |
|---|---|---|---|
| Any automated agent in the swarm | No | No | — |
| `rfp-gates` | No | Yes (to LOW on integrity failure) | Writes `tier_override` with reason |
| Human reviewer via `rfp-review` | Yes (to HIGH) | Yes | Writes `tier_override` with reviewer name + evidence |

A promotion to HIGH requires the reviewer to record:

1. Their identity (`reviewer_id`).
2. Evidence of verification (e.g. "Confirmed SOC 2 Type II report dated 2025-11-14, filed at [link].").
3. Timestamp.

A promotion without all three is rejected by `rfp-review` and the tier stays as assigned.

## 5. Edge Cases

| Case | Rule |
|---|---|
| Two candidates score ≥ 0.90 | Use the freshest `last_approved_date`. If equal, use lexicographically smallest `bank_entry_id` for determinism. |
| Reranker unavailable (index down) | Halt the run. Never fall back to raw vector similarity for tier assignment — the thresholds are calibrated for reranker output. |
| Question returns zero candidates | Tier LOW, `bank_entry_id = "GENERATED"`, `generation_seed = "no_bank_match"`, reviewer required. |
| Reranker returns NaN or out-of-range | Treat as score 0 and tier LOW. Log to stderr. |
| Bank entry has `deprecated: true` | Skip regardless of score; do not use even as a seed. |

## 6. Why These Thresholds

The 0.90 / 0.75 split was calibrated on a 500-question historical sample:

- ≥ 0.90 correlated with "reviewer would have changed nothing" 94% of the time.
- 0.75–0.89 correlated with "reviewer made minor edits" 81% of the time.
- < 0.75 correlated with "reviewer rewrote substantially or rejected" 72% of the time.

Thresholds are not to be tweaked casually. Re-calibration requires a fresh sample of ≥ 300 human-reviewed responses and sign-off from the RFP programme lead.

## 7. Field Reference (in `working/confidence.json`)

```
{
  "question_id": "Q-042",
  "reranker_score": 0.83,
  "tier": "MEDIUM",
  "confidence": 85,
  "adjustments": {
    "category_match_bonus": 5,
    "freshness_bonus": 2,
    "staleness_penalty": 0,
    "length_similarity_bonus": 0,
    "framework_mismatch_penalty": 0
  },
  "rationale": "reranker 0.83 + category match + fresh entry (last approved 2026-02-11)"
}
```

Consumed by `scripts/draft_responses.py` and by the inline progress card.

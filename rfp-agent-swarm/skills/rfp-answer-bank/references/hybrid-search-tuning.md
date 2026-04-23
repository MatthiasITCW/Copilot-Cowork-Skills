# Hybrid Search Tuning

This document describes the query pipeline, scoring, thresholds, and tuning knobs for the answer bank. It covers both the production Azure AI Search configuration and the POC local simulation in `scripts/search_bank.py`.

## 1. Query Pipeline

```
raw_query
  |
  v
[normalize] lowercase, strip punct, collapse whitespace
  |
  v
[expand]    acronym + synonym expansion (see Section 4)
  |
  v
[split]     multi-part detector (see Section 5)
  |
  v
[retrieve]  parallel: BM25 + vector kNN
  |
  v
[fuse]      RRF (reciprocal rank fusion) into single candidate list
  |
  v
[rerank]    semantic cross-encoder over top rerank_depth
  |
  v
[tier]      HIGH / MEDIUM / LOW by reranker score
  |
  v
[filter]    drop deprecated_flag=true; apply category/tag filters
  |
  v
results top_k
```

## 2. Score Aggregation

Three scores per candidate:

| Score | Source | Range |
|---|---|---|
| bm25 | Azure AI Search lexical scorer | 0..inf (log-like) |
| vector | cosine similarity of query embedding vs entry embedding | 0..1 |
| rerank | semantic cross-encoder | 0..1 |

The **rerank score is the sole driver of the confidence tier.** BM25 and vector feed only the candidate-set fusion step. This keeps the tier semantically meaningful and immune to lexical-overlap gaming.

Fusion formula (RRF, k=60):

```
fused_rank_score(doc) = sum over retrievers r of 1 / (60 + rank_r(doc))
```

Top `rerank_depth` fused candidates go into the reranker.

## 3. Confidence Tiers

| Tier | Reranker score | Caller policy |
|---|---|---|
| HIGH | >= 0.90 | Quote verbatim with provenance |
| MEDIUM | 0.75 – 0.89 | Use as seed; reviewer required |
| LOW | < 0.75 | Do not quote; draft fresh in `rfp-respond`; cap at MEDIUM |
| GENERATED | any | Newly synthesized content by `rfp-respond` — capped at MEDIUM regardless of self-eval |

Why HIGH at 0.90: empirically the cross-encoder used (msmarco-MiniLM-L-12-v2 class) hits 0.88+ precision@1 above 0.90. Below 0.75 precision@1 drops below 0.5 — not safe to quote.

## 4. Query Expansion

### Synonym Map

| Canonical | Expansions |
|---|---|
| SSO | single sign-on, single-sign-on, sign on |
| MFA | multi-factor auth, multi-factor authentication, 2FA, two-factor |
| DPA | data processing agreement, data processing addendum |
| SOC 2 | soc two, service organization control 2, soc2 |
| GDPR | general data protection regulation |
| CCPA | california consumer privacy act |
| SLA | service level agreement, uptime commitment |
| SCIM | system for cross-domain identity management, provisioning |
| IdP | identity provider, identity-provider |
| RTO | recovery time objective |
| RPO | recovery point objective |
| PII | personally identifiable information |

### Acronym Expansion Rules

1. If query token matches a known acronym (case-insensitive), inject the expansion as an `OR` term in BM25 and concatenate into the embedded query text.
2. Bidirectional: a query for "multi-factor authentication" also expands to include "MFA".
3. Context-gated acronyms (e.g. "SSO" can mean "single sign-on" or "same-store-sales") are resolved by the category filter when present.

### Abbreviation Normalization

- `soc2` -> `soc 2`
- `iso27001` -> `iso 27001`
- `saml2` -> `saml 2.0`

## 5. Multi-Part Questions

Detector triggers on:
- `;` or ` and ` between independent clauses
- Numbered sub-questions (`(a)`, `1.`, `i.`)
- Question-mark count > 1

Policy:
1. Split into `N` sub-queries.
2. Retrieve top_k per sub-query independently.
3. Merge by `entry_id` with max-rerank-score per entry.
4. Return merged top_k to caller.

Callers in `rfp-respond` must pass the full composite question so provenance reflects the original prompt.

## 6. Tuning Knobs

| Knob | Default | Range | Effect |
|---|---|---|---|
| top_k | 5 | 1–20 | Results returned to caller |
| rerank_depth | 25 | 10–100 | Candidates re-scored by cross-encoder |
| bm25_weight | 0.5 | 0–1 | Fusion weight (diagnostic only; RRF in prod) |
| vector_weight | 0.5 | 0–1 | Fusion weight (diagnostic only) |
| diversity_penalty | 0.0 | 0–0.3 | MMR-style penalty on near-duplicates |
| min_rerank_score | 0.0 | 0–1 | Hard floor for returning any result |
| include_deprecated | false | bool | Never flip to true in prod queries |

### Diversity Penalty

When multiple near-duplicate entries exist (common after sync from Loopio), set `diversity_penalty=0.15` to de-weight subsequent candidates whose embedding cosine to an already-selected candidate exceeds 0.95. Prevents three variants of the same SSO answer monopolizing top_k.

## 7. Category & Tag Filtering

- Pre-filter: `category=security` narrows the BM25/vector pool before rerank. Faster and improves precision when the caller knows the topic.
- Post-filter: `tags` intersection applied after rerank — only removes, never re-ranks.

## 8. POC Local Simulation

`scripts/search_bank.py` implements a stdlib-only approximation:

- **BM25**: `collections.Counter` + `math.log` with k1=1.5, b=0.75 over tokenized canonical_question+answer_text.
- **"Vector"**: character-level Jaccard on token trigrams as a crude proxy. Clearly documented as non-production.
- **"Rerank"**: weighted blend `0.7*bm25_normalized + 0.3*jaccard` then min-max scaled into [0,1].
- Tier thresholds identical to production so callers can't tell the difference at the contract boundary.

This lets every other rfp-* skill develop offline without Azure dependencies.

## 9. Evaluation

Quarterly evaluation set (held-out Q/A pairs from closed RFPs):

| Metric | Target | Notes |
|---|---|---|
| Recall@5 | >= 0.85 | Correct answer in top 5 |
| Precision@1 HIGH | >= 0.90 | Guards HIGH-tier quote policy |
| MRR | >= 0.70 | Mean reciprocal rank |
| Stale-entry rate | <= 5% | Share of top-1 with last_approved_date > 12mo |

A regression on any target blocks a new embedding or reranker model version.

## 10. Common Tuning Scenarios

| Situation | Adjustment |
|---|---|
| Too many MEDIUM drafts being escalated | Raise `rerank_depth` to 50; improves recall into HIGH band |
| Identical-topic duplicates crowding top_k | Set `diversity_penalty=0.15` |
| Buyer uses unusual acronym | Add to synonym map; reindex not required |
| Category collisions (e.g. security vs compliance) | Use `category` pre-filter from caller |
| Cross-encoder latency spikes | Lower `rerank_depth` to 15; monitor precision regression |

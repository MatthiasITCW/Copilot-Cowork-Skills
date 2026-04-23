---
name: rfp-answer-bank
description: Manage the Contoso RFP answer bank — search, add/update, sync Loopio exports, merge reviewer corrections. This is the retrieval substrate that every other rfp-* skill depends on.
triggers:
  - "search the answer bank"
  - "add to KB"
  - "add this to the answer bank"
  - "sync Loopio export"
  - "merge corrections into KB"
  - "answer bank match"
  - "update KB entry"
  - "retire this KB entry"
  - "pull latest from Loopio"
  - "search our RFP library"
---

# rfp-answer-bank

## Shared Infrastructure Ownership

`rfp-answer-bank` is not just a sibling in the `rfp-*` chain — it also owns the **shared infrastructure** that every RFP skill depends on:

1. **The canonical audit log schema.** Defined in `references/audit-log-schema.md`. Every sibling skill writes to `output/rfp-<rfp_id>/audit-log.xlsx` via the script this skill owns.
2. **The xlsx template.** Described in `assets/audit-log-template.md`. The **Excel** built-in materializes the workbook from that spec on first write.
3. **The audit append script.** `scripts/append_audit.py` is the **sole writer** to the audit log. All seven `rfp-*` skills invoke it; none write the xlsx directly.
4. **The audit dashboard renderer.** `scripts/render_audit_dashboard.py` turns a JSON export of the log into a payload for the **Adaptive Cards** built-in — this is what answers "show me the RFP audit trail for RFP-XXXX".
5. **The canonical Event Type Catalogue.** New event types must be added to `references/audit-log-schema.md` before any skill may emit them.

This means: if a sibling skill needs to record an event, it does not define its own log format — it uses the schema here.

## Built-In Skills Used

| Cowork built-in | How this skill uses it |
|---|---|
| **Excel** | Appends rows to `audit-log.xlsx`; exports `AuditLog` sheet as JSON for the dashboard; exports KB snapshots for analysts |
| **Adaptive Cards** | Renders search-match cards, corrections-merge delta cards, and the shared RFP audit-trail dashboard |
| **Enterprise Search** | Fallback retrieval across SharePoint when the answer bank returns LOW tier for a question |
| **Deep Research** | Invoked for novel questions where no bank entry exists and a net-new, well-cited draft is needed (result is fed to `rfp-respond`, not written back to the bank unauthenticated) |

## 1. Purpose

The answer bank is the single retrieval substrate for the RFP Agent Swarm POC. Every draft answer, fit-assessment match estimate, gate check, and reviewer correction routes through this skill. Loopio remains the system-of-record for **approved** Q&A, but Loopio alone cannot power a 15-agent parallel drafting swarm: it offers keyword search only, rate-limits aggressive pollers, and lacks a reranker score we can threshold on. The answer bank closes those gaps by projecting Loopio into Azure AI Search (semantic + vector + hybrid) and augmenting it with reviewer corrections.

This skill owns four operations against that substrate:
1. **Search** — hybrid query with confidence tiering.
2. **CRUD** — add, update, retire individual entries.
3. **Sync** — ingest Loopio exports on a schedule.
4. **Merge** — apply approved corrections from `rfp-review`.

Retrieval-first philosophy: **never draft from the model's parametric memory when the bank contains a HIGH-tier match**. The bank is deliberately the boring, conservative layer. New synthesis happens in `rfp-respond` and is always capped at MEDIUM tier.

## 2. When to Use (Triggers)

Invoke this skill when any of the following phrases appear, or when another skill programmatically calls it:

- "search the answer bank"
- "add to KB" / "add this to the answer bank"
- "sync Loopio export" / "pull latest from Loopio"
- "merge corrections into KB"
- "answer bank match" (called by `rfp-fit-assessment`)
- "update KB entry"
- "retire this KB entry"
- "search our RFP library"
- Any retrieval call from `rfp-respond` per question
- Any provenance lookup from `rfp-assemble`

## 3. Do NOT Use For

| Situation | Correct skill |
|---|---|
| Classifying incoming RFPs into sections / questions | `rfp-intake` |
| Deciding whether to bid (go/no-go) | `rfp-fit-assessment` |
| Drafting a net-new answer when the bank returns LOW tier | `rfp-respond` |
| Checking a draft against approved certification / pricing lists | `rfp-gates` |
| Human sign-off loop on draft answers | `rfp-review` |
| Final document assembly / provenance rendering | `rfp-assemble` |
| Storing buyer-specific tone or voice preferences | `deal-room` |
| Legal redlining of contract clauses | `legal-redliner` |

Do **not** use this skill as a general document search over policies, SOC 2 reports, or marketing collateral — the bank is scoped to discrete question/answer pairs with approval provenance.

## 4. Data Flow

```
 Loopio (system of record, keyword only)
    |
    |  manual XLSX export (POC) / scheduled Azure Function (future)
    v
 Azure Blob Storage (raw export landing zone)
    |
    |  indexer run (schema mapping, dedup, deprecation flagging)
    v
 Azure AI Search index (hybrid: BM25 + vector + semantic reranker)
    ^
    |  hybrid queries from 15 parallel agents
    |
 rfp-respond / rfp-fit-assessment / rfp-gates / rfp-assemble
    |
    |  drafts reviewed -> corrections.jsonl
    v
 rfp-review ---- export_corrections ----> merge_corrections.py
    |
    +--> updates/adds/retirements applied back into index
    +--> (future two-way sync) pushed back into Loopio
```

Key invariant: **Loopio -> bank is one-way today**. Corrections land in the bank first; two-way sync to Loopio is a deliberate Phase-2 scope item.

## 5. Workflow

### 5.1 Search
1. Receive `query` (plus optional `category`, `tags`, `top_k`).
2. Expand acronyms / synonyms (see `references/hybrid-search-tuning.md`).
3. Issue hybrid query: BM25 + vector (embedding) + semantic reranker.
4. Apply confidence tier (HIGH ≥0.9, MEDIUM 0.75–0.89, LOW <0.75).
5. Exclude any entry with `deprecated_flag=true`.
6. Return top_k with full provenance so `rfp-respond` and `rfp-assemble` can cite.

### 5.2 Add / Update / Retire
- Add: validate required fields, generate `entry_id` (UUID4), set `version=1`.
- Update: preserve old version in history, bump `version`, require `approved_by`.
- Retire: set `deprecated_flag=true` and optionally populate `replaces[]` on the successor.
- Hard delete is **forbidden**. Use retirement.

### 5.3 Sync Loopio Export
1. Read exported CSV/XLSX-text-dump from Azure Blob (local file for POC).
2. Map columns to schema; skip malformed rows with stderr log.
3. Diff against current bank by `source_loopio_entry_id`.
4. Apply adds / updates; mark rows missing from export as candidates for deprecation (manual confirm).
5. Emit `sync_report.json` with counts and conflict list.

### 5.4 Merge Corrections
1. Load `corrections.jsonl` produced by `rfp-review`.
2. For each correction verify reviewer sign-off fields present.
3. Apply the rule in `references/corrections-merge-rules.md` keyed on `reason`.
4. Emit `merge_report.json` keyed by reason.
5. Idempotent: replaying the same file applies no additional changes.

## 6. Confidence Tiers

| Tier | Reranker score | Policy |
|---|---|---|
| HIGH | >= 0.90 | Use verbatim with provenance; `rfp-respond` must not rewrite |
| MEDIUM | 0.75 – 0.89 | Use as draft seed; `rfp-respond` may light-edit; reviewer required |
| LOW | < 0.75 | Do not quote; `rfp-respond` drafts fresh; capped at MEDIUM post-hoc |
| GENERATED | n/a | Any content synthesized by `rfp-respond` is capped at MEDIUM regardless of self-eval |

## 7. Schema Overview

See `references/answer-bank-schema.md` for the full spec. Quick view:

| Field | Type | Notes |
|---|---|---|
| entry_id | UUID | Stable, bank-owned |
| question_text | string | Verbatim prompt |
| canonical_question | string | Normalized for dedup |
| answer_text | string | Approved response body |
| category / subcategory | enum / free | See enums in schema doc |
| tags | string[] | Free-form; lowercased |
| source | enum | loopio_entry_id \| internal_sme \| correction |
| last_approved_date | ISO date | Gate for staleness |
| approved_by | email | Required for internal_sme and correction |
| version | int | Monotonic per entry_id |
| deprecated_flag | bool | Excluded from search |
| replaces | UUID[] | Points to predecessors |
| certifications_referenced | string[] | Cross-ref `rfp-gates` list |
| pricing_reference_ids | string[] | Cross-ref pricing registry |
| evidence_attachments | url[] | SharePoint / Blob links |

## 8. Guardrails

- **Never fabricate an entry.** If a question has no match, the answer is "no match" — not a hallucinated seed.
- **Never auto-merge a correction without reviewer sign-off.** `merge_corrections.py` refuses records missing `reviewed_by` and `reviewed_at`.
- **Never return deprecated entries in search.** Filter is applied server-side and re-asserted client-side in `search_bank.py`.
- **Never hard-delete.** Use `deprecated_flag=true` and populate `replaces[]` on the successor to preserve audit trail.
- **Never allow unapproved source types.** Allowed: `loopio_entry_id`, `internal_sme`, `correction`.
- **Never quote a LOW-tier result.** The tier is advisory for callers; `rfp-respond` enforces the quoting rule.
- **Never write directly from a raw Loopio row.** Rows must pass schema validation in `sync_loopio_export.py`.
- **Never let generated content claim HIGH.** Tier is capped per the table in Section 6.
- **Never bypass the sign-off staleness guard.** Corrections older than 90 days must be re-reviewed.
- **Never mutate a historical version.** Corrections against an older `version` create a new current version.

### Contract Boundaries

| Upstream skill | Contract it honors |
|---|---|
| `rfp-intake` | Emits canonical question list; this skill receives those verbatim for retrieval |
| `rfp-review` | Emits `corrections.jsonl` with sign-off metadata; this skill is the sole consumer |
| `rfp-respond` | Treats tier as binding; does not rewrite HIGH-tier answers |
| `rfp-gates` | Treats `certifications_referenced[]` / `pricing_reference_ids[]` as authoritative cross-refs |
| `rfp-assemble` | Uses `entry_id` + `version` as provenance keys; this skill guarantees they are stable |

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All queries return LOW tier | Vector index not warm / reranker unavailable | Fall back to BM25-only path; escalate to platform-ops; do not draft from LOW |
| Sync report shows large `deprecated_count` spike | Loopio export truncated or filtered | Re-export full set; do not apply the sync; compare row counts to Loopio dashboard |
| `add_entry.py` rejects with "missing approved_by" | source=internal_sme without approver | Require SME sign-off email; re-run |
| Duplicate entries for same canonical_question | Canonicalization drift across syncs | Run dedup pass; retire the older; populate `replaces[]` |
| Corrections apply once then duplicate on replay | Correction file lacks `correction_id` or idempotency key | Regenerate export from `rfp-review` with IDs; re-run merge |
| Search returns a retired entry | Cached client or filter skipped | Purge local cache; verify `deprecated_flag=true` filter in request |
| Hybrid score much lower than BM25 alone | Embedding model drift after reindex | Re-embed corpus; confirm model version pinned |
| `merge_corrections.py` raises on TONE_OR_STYLE | Treated as KB change incorrectly | Expected NO-OP at bank level; log only; do not mutate entry |
| Two conflicting corrections on same entry | Race between reviewers | Last-writer-wins by `reviewed_at`; older correction surfaces in conflicts[] |
| `sync_loopio_export.py` silently drops rows | Malformed header or encoding | Inspect stderr log; re-export as UTF-8 CSV |

## 10. Audit Log

`rfp-answer-bank` owns the shared audit log (see `references/audit-log-schema.md`). In addition to being the schema host, this skill itself emits the following event types into `output/rfp-<rfp_id>/audit-log.xlsx`:

| Event Type | When emitted | Typical `before` / `after` |
|---|---|---|
| `BANK_SEARCHED` | Every hybrid-search call, whether from humans or other `rfp-*` skills | `before=null`, `after={"top_k":5,"top_tier":"HIGH","top_confidence":0.92}` |
| `KB_ENTRY_ADDED` | `add_entry.py` creates a new entry | `before=null`, `after={"entry_id":"...","version":1}` |
| `KB_ENTRY_UPDATED` | `add_entry.py` bumps version or flips `deprecated_flag` | `before={"version":2}`, `after={"version":3}` |
| `LOOPIO_SYNC_COMPLETED` | `sync_loopio_export.py` finishes | `after={"added":N,"updated":M,"deprecated_candidates":K}` |
| `CORRECTIONS_MERGED` | `merge_corrections.py` finishes a batch | `after={"applied":N,"no_ops":K,"conflicts":J}` |

All writes go through `scripts/append_audit.py`, which validates that these event types belong to `rfp-answer-bank` and stamps `event_id` + `timestamp_utc`. The file is created on first write by the **Excel** built-in per `assets/audit-log-template.md`.

See `references/audit-log-schema.md` for the full column list, integrity rules, and cross-skill Event Type Catalogue.

## 11. Adaptive Card Dashboard

This skill produces three kinds of Adaptive Cards via the **Adaptive Cards** built-in:

### 11.1 Search-match card (on every `BANK_SEARCHED`)
- Header: the query text and the returned tier (HIGH / MEDIUM / LOW).
- Body: top-N entries (default N=3), each with `entry_id`, short excerpt, category, `confidence` badge color-coded to tier.
- Footer: a diff preview when the top match is a **correction-augmented** version of a prior Loopio entry, so the caller can see what changed vs. the system-of-record.

### 11.2 Corrections-merge delta card (on every `CORRECTIONS_MERGED`)
- Header: source file + merge timestamp.
- Body: counts of entries added / updated / retired, grouped by `reason`.
- Footer: **expected match-rate lift** — the delta between the pre-merge and post-merge estimated HIGH-tier rate on the last replayed query set (cached from `rfp-fit-assessment`).

### 11.3 RFP audit-trail dashboard (on "show me the RFP audit trail for RFP-XXXX")
The renderer is `scripts/render_audit_dashboard.py`. Pipeline:

1. The **Excel** built-in exports `AuditLog` from `audit-log.xlsx` as JSON.
2. `render_audit_dashboard.py --audit-json <path> --rfp-id RFP-XXXX` emits the card payload.
3. The **Adaptive Cards** built-in renders it.

Payload contents:
- **KPI row:** total events, AI vs human split, last update time.
- **Timeline:** events bucketed by hour.
- **Event-type distribution:** donut, one slice per event type.
- **Actor distribution:** donut (ai / human).
- **Event stream:** the 25 most recent rows with skill, event_type, target, reason.

This is the single pane of glass any operator uses to understand what the swarm did to an RFP from first `RFP_INTAKE_STARTED` through `RECORD_SET_PACKAGED`.

## 12. Related Skills

### RFP chain
`rfp-answer-bank` is the **retrieval substrate and audit-log host** for the chain:

```
  rfp-intake ──► rfp-fit-assessment ──► rfp-respond ──► rfp-gates ──► rfp-review ──► rfp-assemble
        │               │                   │               │              │               │
        └──────────┬────┴───────────────────┴───────────────┴──────────────┴───────────────┘
                   │ writes events to
                   ▼
              rfp-answer-bank
            (audit log + KB)
                   ▲
                   │ reads for match-rate (fit-assessment),
                   │ retrieval (respond), provenance (assemble)
                   │ corrections in (from review)
```

- **Feeds `rfp-respond`** — per-question hybrid retrieval, tier-binding policy.
- **Read by `rfp-fit-assessment`** — pre-bid coverage / match-rate estimate.
- **Receives corrections from `rfp-review`** — the only sanctioned mutation path.
- **Supplies provenance to `rfp-assemble`** — `entry_id` + `version` are stable keys.
- **Cross-refs `rfp-gates`** — `certifications_referenced[]` / `pricing_reference_ids[]`.
- **Bootstrapped by `rfp-intake`** — first `RFP_INTAKE_STARTED` event creates the audit workbook.

### Cowork built-ins leveraged
- **Excel** — appends audit-log rows; exports `AuditLog` as JSON for the dashboard; exports KB snapshots for analysts.
- **Adaptive Cards** — renders search-match cards, corrections-merge delta cards, and the RFP audit-trail dashboard.
- **Enterprise Search** — fallback retrieval across SharePoint when the bank returns LOW tier.
- **Deep Research** — novel-question fallback when no bank entry exists; output feeds `rfp-respond` (never written back to the bank without reviewer sign-off).

### Adjacent (non-chain) skills
- [`audit-readiness`](../audit-readiness/SKILL.md) — consumes version history for evidence.
- [`legal-review`](../legal-review/SKILL.md) — may attach corrections with reason=POLICY_UPDATE.

### Cross-links
- Audit log schema: `references/audit-log-schema.md`
- Audit log template: `assets/audit-log-template.md`
- Answer-bank schema: `references/answer-bank-schema.md`
- Hybrid search tuning: `references/hybrid-search-tuning.md`
- Loopio sync playbook: `references/loopio-sync-playbook.md`
- Correction merge rules: `references/corrections-merge-rules.md`
- SME entry template: `assets/kb-entry-template.md`
- Scripts: `scripts/search_bank.py`, `scripts/add_entry.py`, `scripts/sync_loopio_export.py`, `scripts/merge_corrections.py`, `scripts/append_audit.py`, `scripts/render_audit_dashboard.py`

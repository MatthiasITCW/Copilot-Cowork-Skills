# Loopio Sync Playbook

## 1. Scope

Loopio is the Contoso system-of-record for approved RFP Q&A. The answer bank is a downstream projection that adds hybrid search and reviewer correction capabilities. **Loopio remains authoritative for approvals; the bank augments, it does not replace.**

## 2. POC Flow (Manual)

```
1. RFP Ops exports Loopio library to XLSX (weekly cadence)
2. Save as UTF-8 CSV (keep Excel formatting out of text fields)
3. Upload to Azure Blob container: rfp-bank-raw/loopio/YYYY-MM-DD.csv
4. Trigger Azure AI Search indexer run (or invoke scripts/sync_loopio_export.py for local POC)
5. Review sync_report.json: added_count, updated_count, deprecated_candidates, conflicts
6. RFP Ops manually confirms deprecation candidates (see Section 6)
```

## 3. Expected Loopio Export Columns -> Bank Schema

| Loopio column | Bank field | Transform |
|---|---|---|
| Entry ID | source_loopio_entry_id | Verbatim |
| Question | question_text | Trim whitespace |
| Answer | answer_text | Strip HTML tags; preserve line breaks |
| Category | category | Map via category enum table below |
| Tags | tags | Split on comma; lowercase; deduplicate |
| Last Reviewed | last_approved_date | Parse to ISO date (UTC) |
| Reviewed By | approved_by | Verbatim email |
| Status | — | Only `Published` rows imported; `Draft` skipped |
| Certifications | certifications_referenced | Split on comma; uppercase; normalize |
| Pricing Ref | pricing_reference_ids | Split on comma |
| Attachments | evidence_attachments | Split on `|` |

### Loopio Category Mapping

| Loopio label | Bank enum |
|---|---|
| Security & Infosec | security |
| Privacy | privacy |
| Compliance & Certifications | compliance |
| Product Features | product |
| Integrations / APIs | integrations |
| Support & Ops | operations |
| Pricing & Commercial | commercial |
| Legal & Contracts | legal |
| Company Overview | company |
| Other / Misc | other |

## 4. Deduplication

- Primary key for matching: `source_loopio_entry_id`.
- If a Loopio entry is renamed (ID stable, question_text changed), we treat it as an **update**, not a new entry. `version` bumps; old text moves to `history[]`.
- If a Loopio entry is deleted (ID gone from export), it becomes a **deprecation candidate**. We do NOT auto-deprecate — a human confirms (Section 6).
- If the same `canonical_question` appears under two different Loopio IDs, flag as a `duplicate` conflict. Merge is manual.

## 5. Conflict Handling

The bank can contain entries whose most recent change came from a reviewer correction (via `rfp-review`) rather than Loopio. When a sync arrives for such an entry:

| Situation | Resolution |
|---|---|
| Loopio answer matches bank answer | No-op |
| Loopio answer differs, bank version came from correction | **Correction wins.** Flag in conflicts[] for later round-trip into Loopio |
| Loopio answer differs, bank version came from Loopio | Loopio wins. Version bumped |
| Loopio entry missing, bank version came from correction | Keep bank entry; do not deprecate |
| Loopio entry missing, bank version came from Loopio | Add to deprecation candidates |

The "correction wins" rule ensures approved reviewer edits are never silently overwritten by stale Loopio content. A future two-way sync will push these corrections back into Loopio.

## 6. Deprecation Confirmation

`sync_loopio_export.py` emits `deprecation_candidates[]` but never flips `deprecated_flag=true` automatically. RFP Ops reviews the list and runs `add_entry.py` or a deprecation helper to confirm. Rationale: a botched Loopio export (wrong filter, truncated download) would otherwise mass-deprecate good entries.

## 7. Future: Timer-Triggered Azure Function

Target Phase 2:

```
Azure Function (cron: 0 */6 * * *)
  -> Loopio REST API: GET /v2/library-entries?updated_since=<last_watermark>
  -> landing blob: rfp-bank-raw/loopio/incremental/<timestamp>.json
  -> indexer runs on blob trigger
  -> watermark advanced on success
```

Open questions:
- Loopio API rate limits: need burst + steady-state numbers
- Auth: service principal vs API key
- Delta semantics: does Loopio report deletes, or must we diff?
- Two-way sync: push correction-origin entries back via `PATCH /v2/library-entries/{id}`

## 8. Boundary Rules

1. **Loopio is source of truth for approvals.** New SME-authored entries go into Loopio first when possible, then flow through sync.
2. **Bank-only entries are allowed** (source=internal_sme or correction) but must be reviewed for back-porting to Loopio quarterly.
3. **Never treat Loopio as the retrieval substrate at runtime.** Keyword-only + rate limits = unacceptable for 15 parallel agents.
4. **Never draft an answer from a Draft-status Loopio row.** Skip at sync time.
5. **Loopio `Published` status is not sufficient for HIGH tier** — the reranker score still governs tier.

## 9. Runbook: First-Time Sync

1. Ensure `bank.jsonl` is empty or intentionally seeded.
2. Export the full Loopio library (not incremental).
3. Run `sync_loopio_export.py --export-file <path> --bank-file working/bank.jsonl --output working/sync_report.json`.
4. Verify `added_count` roughly matches Loopio `Published` row count.
5. Spot-check 20 random entries for schema fidelity.
6. Re-run once; expect zero changes (idempotent).

## 10. Runbook: Troubleshooting Sync

| Symptom | Diagnosis | Action |
|---|---|---|
| UnicodeDecodeError | Export saved as CP-1252 | Re-save as UTF-8 CSV |
| Added-count far exceeds expected | Previous `bank.jsonl` pointed to wrong path | Restore prior bank; re-run |
| Many "duplicate canonical_question" conflicts | Canonicalization rule changed | Re-run full reindex; normalize |
| Deprecation candidates include recently-added rows | Export was filtered by category | Re-export unfiltered; discard current report |
| approved_by blank on sync | Loopio "Reviewed By" column missing for legacy entries | Backfill via bulk update in Loopio; do not default to a placeholder |
| Sync succeeds but index returns stale rows | Indexer not triggered | Manually run indexer; verify high-water mark advanced |

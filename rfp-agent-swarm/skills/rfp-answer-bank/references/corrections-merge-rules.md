# Corrections Merge Rules

This document defines the merge behavior for each correction reason emitted by `rfp-review` via its `export_corrections` operation. `scripts/merge_corrections.py` implements these rules exactly.

## 1. Correction Record Shape

```json
{
  "correction_id": "c-2026-04-22-0007",
  "target_entry_id": "b1b2a0c4-2c9f-4f52-9f14-6ab5df3d1e2a",
  "rfp_id": "RFP-8821",
  "question_text": "Do you encrypt customer data at rest?",
  "original_answer": "...",
  "corrected_answer": "...",
  "reason": "FACTUAL_ERROR",
  "reviewer_notes": "AES-256 not AES-128",
  "reviewed_by": "ciso@contoso.com",
  "reviewed_at": "2026-04-22T10:14:00Z",
  "sign_off_token": "eyJ..."
}
```

**Any record missing `reviewed_by`, `reviewed_at`, or `sign_off_token` is rejected at merge time.** No exceptions.

## 2. Reason Taxonomy and Merge Rules

| Reason | KB action | Version effect | `last_approved_date` effect | Notes |
|---|---|---|---|---|
| FACTUAL_ERROR | Update existing entry | Bump +1 | Set to `reviewed_at` date | Old version retained in history[]; change_note populated |
| OUTDATED_SOURCE | Update existing entry | Bump +1 | Set to `reviewed_at` date | Typically a date-reference refresh |
| TONE_OR_STYLE | NO-OP at KB level | none | none | Logged in merge report; tone is buyer-specific, not KB-wide |
| MISSING_CONTEXT | Add new sibling entry | New entry v1 | set to `reviewed_at` | Tag with `context:<rfp_id>`; original remains |
| CATEGORY_MISCLASSIFICATION | Re-tag only | Bump +1 (no text change) | unchanged | Fields changed: category / subcategory / tags |
| UNANSWERABLE_FROM_KB | Add new entry | New entry v1 | set to `reviewed_at` | source=internal_sme (SME authored during review) |
| POLICY_UPDATE | Retire old + add successor | Successor v1; predecessor deprecated_flag=true | Successor set to `reviewed_at` | Populate `replaces[]` on successor |
| COMPLIANCE_NUANCE | Add jurisdiction sibling | New entry v1 | set to `reviewed_at` | Tag with `jurisdiction:<code>` (e.g. `jurisdiction:eu`) |

## 3. Detailed Procedures

### FACTUAL_ERROR
1. Load target entry by `target_entry_id`.
2. Snapshot current version to `history[]` with `change_note = "correction_id=<id>: " + reviewer_notes`.
3. Replace `answer_text` with `corrected_answer`.
4. `version += 1`; set `last_approved_date = reviewed_at.date`; `approved_by = reviewed_by`.
5. `source` becomes `correction` (even if original was `loopio_entry_id`) so sync knows correction wins on next Loopio pass.
6. Write.

### OUTDATED_SOURCE
Identical to FACTUAL_ERROR mechanically. Separated for reporting and to allow later divergent logic (e.g. auto-schedule re-review).

### TONE_OR_STYLE
1. Record in `merge_report.json` under `skipped[]`.
2. Do **not** touch the entry.
3. Rationale: tone/style is buyer-specific and handled in `rfp-respond` using `deal-room` voice preferences — it should not contaminate shared KB.

### MISSING_CONTEXT
1. Keep the original entry.
2. Create a new entry:
   - `question_text` = original question or `correction.question_text`
   - `answer_text` = `corrected_answer`
   - `category` inherited from original
   - `tags` = original.tags + `["context:" + rfp_id]`
   - `source` = `correction`
   - `approved_by` = `reviewed_by`
3. Do not populate `replaces[]` — both entries remain active.

### CATEGORY_MISCLASSIFICATION
1. Load target entry.
2. Update `category` / `subcategory` / `tags` per correction fields (`corrected_answer` field conveys the tag payload as JSON in this case; parser documented in `merge_corrections.py`).
3. Bump version; `change_note = "retag: <old> -> <new>"`.
4. `answer_text` unchanged.

### UNANSWERABLE_FROM_KB
1. No target_entry_id expected (or empty).
2. Create a brand-new entry:
   - `source = internal_sme`
   - `approved_by = reviewed_by`
   - `version = 1`
   - `tags` include `origin:rfp-review`
3. Useful when reviewer writes an answer from scratch because the KB had nothing.

### POLICY_UPDATE
1. Load target entry; set `deprecated_flag = true`; add `history[]` snapshot with `change_note = "superseded by correction <id>"`.
2. Create successor entry:
   - `answer_text = corrected_answer`
   - `replaces = [target_entry_id]`
   - `version = 1`
   - `source = correction`
   - `approved_by = reviewed_by`
3. Both writes in same transaction (script ensures atomicity: writes to a temp file then renames).

### COMPLIANCE_NUANCE
1. Keep original active.
2. Create jurisdiction-scoped sibling:
   - `tags += ["jurisdiction:" + code]` (code inferred from correction payload; defaults to `other` with warning)
   - `answer_text = corrected_answer`
   - `source = correction`

## 4. Idempotency

`merge_corrections.py` writes `applied_correction_ids` into a sidecar file `working/bank.applied.json`. On re-run:
- If `correction_id` already present, skip (not an error).
- Report in `merge_report.json` under `skipped_duplicates[]`.
- Guarantees that re-running the same file is safe.

## 5. Conflict Handling During Merge

| Conflict | Resolution |
|---|---|
| Target entry already deprecated | Reject correction; put in `conflicts[]` with reason |
| Target entry not found | Reject correction; put in `conflicts[]` |
| Two corrections target same entry in one batch | Apply in `reviewed_at` order; later one layered on earlier |
| Correction for entry whose version has advanced since reviewer saw it | Still apply, but `change_note` records both correction_id and "applied on top of vN" |

## 6. Reporting

`merge_report.json` schema:

```json
{
  "merged_at": "2026-04-22T12:00:00Z",
  "total_input": 42,
  "applied_by_reason": {
    "FACTUAL_ERROR": 9,
    "OUTDATED_SOURCE": 4,
    "TONE_OR_STYLE": 0,
    "MISSING_CONTEXT": 3,
    "CATEGORY_MISCLASSIFICATION": 6,
    "UNANSWERABLE_FROM_KB": 11,
    "POLICY_UPDATE": 2,
    "COMPLIANCE_NUANCE": 5
  },
  "skipped": [ {"correction_id": "...", "reason_code": "TONE_OR_STYLE"} ],
  "skipped_duplicates": [ "..." ],
  "conflicts": [ {"correction_id": "...", "why": "target not found"} ],
  "affected_entry_ids": [ "..." ]
}
```

## 7. Sign-Off Verification

The `sign_off_token` is an opaque string generated by `rfp-review` when a human reviewer approves the correction. `merge_corrections.py` verifies:
1. Token is non-empty.
2. `reviewed_by` is a valid Contoso email (@contoso.com) — warn-only in POC, enforced in prod.
3. `reviewed_at` is within the last 90 days (staleness guard).

Any failure -> correction rejected and logged in `conflicts[]`.

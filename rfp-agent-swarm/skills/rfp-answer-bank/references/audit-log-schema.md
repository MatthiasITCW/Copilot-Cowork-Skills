# Shared RFP Audit Log — Canonical Schema

This document defines the **single shared audit log** that every `rfp-*` skill writes to. `rfp-answer-bank` owns the schema definition, the xlsx template, and the dashboard renderer. All sibling skills (`rfp-intake`, `rfp-fit-assessment`, `rfp-respond`, `rfp-gates`, `rfp-review`, `rfp-assemble`) link back to this file rather than defining their own log formats.

## 1. Location & Naming

```
output/rfp-<rfp_id>/audit-log.xlsx
```

- **One file per RFP.** The file is created when `rfp-intake` fires its first `RFP_INTAKE_STARTED` event and lives alongside the rest of the RFP record set.
- The `<rfp_id>` segment matches the ID assigned by `rfp-intake` (e.g. `RFP-2026-042`).
- There is no global / cross-RFP audit log in the POC; cross-RFP reporting is derived by scanning the per-RFP files.

## 2. Workbook Structure

- Single sheet named **`AuditLog`**.
- No second sheet, no pivot caches — downstream dashboards are rendered by `scripts/render_audit_dashboard.py`, not by Excel formulas.
- The workbook is created by the **Excel** built-in the first time `scripts/append_audit.py` emits a row for an RFP that has no existing file.
- All appends go through the **Excel** built-in. No skill writes the xlsx directly.

## 3. Column Schema

| Column | Type | Example | Purpose |
|---|---|---|---|
| `event_id` | UUID (hex, no dashes) | `8b2c4f91e4d74c1aa1b2c3d4e5f6a7b8` | Unique, immutable identifier for this event. Primary key. |
| `timestamp_utc` | ISO 8601 string (Zulu) | `2026-04-22T10:17:34Z` | When the event fired. Auto-generated; never backdated. |
| `rfp_id` | string | `RFP-2026-042` | Links every row to exactly one RFP. Redundant with filename for portability when rows are exported. |
| `skill` | string (enum) | `rfp-respond` | Which `rfp-*` skill wrote the event. One of the seven canonical siblings. |
| `event_type` | string (enum) | `RESPONSE_DRAFTED` | Must be a member of the Event Type Catalogue in section 4. Validation is enforced by `append_audit.py`. |
| `actor` | string (enum) | `ai` | Either `ai` or `human`. Mixed agent-plus-human actions are split into two rows. |
| `actor_id` | string | `admin@contoso.com` / `agent-rfp-respond-03` | Identity of the actor. Email for humans, agent-id for AI. |
| `target_type` | string (enum) | `question` | One of: `question`, `gate`, `correction`, `deliverable`, `kb_entry`. |
| `target_id` | string | `Q-014` / `GATE-SEC` / `KB-9821` | Identifier of the affected entity. |
| `before` | JSON string | `{"tier":"LOW"}` | Prior state of the target. `null` for creation events. |
| `after` | JSON string | `{"tier":"HIGH","source":"KB-9821"}` | New state of the target. `null` for pure read events like `BANK_SEARCHED`. |
| `reason` | string | `outdated KB entry` | Human-readable justification. Required on correction events; optional elsewhere. |
| `provenance_id` | string | `KB-9821` / `generated+reviewed` | Traces the event back to a KB entry, or marks output as generated-and-reviewed. |
| `confidence` | number 0-1 | `0.92` | Confidence score when applicable (search, gate check, scorecard). Blank otherwise. |
| `notes` | string | `fallback to Enterprise Search` | Free-text context. Optional. |

## 4. Event Type Catalogue

The canonical list of valid `event_type` values. `append_audit.py` rejects any value not in this list.

| Skill | Event Types |
|---|---|
| `rfp-intake` | `RFP_INTAKE_STARTED`, `QUESTION_EXTRACTED`, `CLASSIFICATION_APPLIED`, `TASK_LIST_CREATED`, `INTAKE_COMPLETE` |
| `rfp-fit-assessment` | `FIT_ASSESSMENT_STARTED`, `SCORECARD_COMPUTED`, `GO_NO_GO_RECOMMENDED`, `HUMAN_DECISION_LOGGED` |
| `rfp-respond` | `RESPONSE_DRAFT_STARTED`, `KB_MATCH_FOUND`, `RESPONSE_GENERATED`, `TEAM_ROUTED`, `RESPONSE_BATCH_COMPLETE` |
| `rfp-gates` | `GATE_REQUESTED`, `GATE_APPROVED`, `GATE_REJECTED`, `PIPELINE_PAUSED`, `PIPELINE_RESUMED` |
| `rfp-review` | `REVIEW_QUEUE_BUILT`, `CORRECTION_CAPTURED`, `CORRECTION_REASON_TAGGED`, `REVIEW_COMPLETE` |
| `rfp-assemble` | `ASSEMBLY_STARTED`, `FORMAT_SELECTED`, `DELIVERABLE_GENERATED`, `ANALYTICS_COMPUTED`, `RECORD_SET_PACKAGED` |
| `rfp-answer-bank` | `BANK_SEARCHED`, `KB_ENTRY_ADDED`, `KB_ENTRY_UPDATED`, `LOOPIO_SYNC_COMPLETED`, `CORRECTIONS_MERGED` |

New event types must be added to this catalogue **before** any skill is permitted to emit them. The catalogue is the single source of truth.

## 5. Retention

- The audit log persists for the RFP's entire lifecycle — from first `RFP_INTAKE_STARTED` through `RECORD_SET_PACKAGED` and beyond.
- The file is part of the RFP's record set and follows the same retention policy as the deliverables themselves.
- No rotation, no truncation: every event ever written for the RFP remains queryable.

## 6. Integrity Rules

1. **`event_id` is immutable.** Once written, it is never reused, rewritten, or reassigned.
2. **Append-only.** There is no delete operation. `append_audit.py` exits non-zero if asked to produce a delete.
3. **Corrections are new events.** If a prior event was wrong, a new event is written with `before` set to the prior state's `after` and `after` set to the corrected state. The original row is never mutated.
4. **Timestamps are server-generated.** `append_audit.py` stamps `timestamp_utc` from the wall clock; callers cannot override it. This prevents backdating.
5. **Event-type validation is strict.** Unknown `event_type` values are rejected at write time.
6. **`before`/`after` must be valid JSON.** Empty strings are coerced to `null`.

## 7. Access Pattern

| Operation | Who performs it | How |
|---|---|---|
| Append a row | Any `rfp-*` skill | Calls `scripts/append_audit.py` → pipes the emitted JSON row to the **Excel** built-in, which appends it to `AuditLog` |
| Read the log | Dashboard renderer | The **Excel** built-in exports `AuditLog` as JSON; `scripts/render_audit_dashboard.py` consumes that JSON |
| Render the dashboard | `rfp-answer-bank` | The **Adaptive Cards** built-in consumes the payload emitted by `render_audit_dashboard.py` |
| Ad-hoc query | Human analyst | Opens the xlsx directly; filters are pre-enabled on every column |

## 8. Cross-Skill Contract

Every sibling `rfp-*` skill must:
- Emit at least one event per major state transition it owns.
- Use only `event_type` values from its row in section 4.
- Reference this schema file rather than duplicating the column list.
- Route all writes through `scripts/append_audit.py` (owned by `rfp-answer-bank`).

Sibling skills **must not**:
- Define their own audit log format.
- Write the xlsx file directly — only the **Excel** built-in writes, and only at the direction of `append_audit.py`.
- Invent new `event_type` values without first amending section 4 here and re-releasing `append_audit.py`.

## 9. Typical Event Sequence

A well-behaved RFP produces events roughly in this order:

1. `RFP_INTAKE_STARTED` — workbook is created; sheet `AuditLog` seeded with header row.
2. `QUESTION_EXTRACTED` × N — one per question parsed from the source RFP.
3. `CLASSIFICATION_APPLIED`, `TASK_LIST_CREATED`, `INTAKE_COMPLETE`.
4. `FIT_ASSESSMENT_STARTED` → `SCORECARD_COMPUTED` → `GO_NO_GO_RECOMMENDED` → `HUMAN_DECISION_LOGGED`.
5. `BANK_SEARCHED` × N (from `rfp-answer-bank`, invoked by `rfp-respond`).
6. `RESPONSE_DRAFT_STARTED` → `KB_MATCH_FOUND` / `RESPONSE_GENERATED` → `TEAM_ROUTED` → `RESPONSE_BATCH_COMPLETE`.
7. `GATE_REQUESTED` → `GATE_APPROVED` or `GATE_REJECTED` → possibly `PIPELINE_PAUSED` / `PIPELINE_RESUMED`.
8. `REVIEW_QUEUE_BUILT` → `CORRECTION_CAPTURED` × K → `CORRECTION_REASON_TAGGED` → `REVIEW_COMPLETE`.
9. `CORRECTIONS_MERGED` (from `rfp-answer-bank`, after `rfp-review` exports).
10. `ASSEMBLY_STARTED` → `FORMAT_SELECTED` → `DELIVERABLE_GENERATED` → `ANALYTICS_COMPUTED` → `RECORD_SET_PACKAGED`.

This sequence is a **guideline**, not a constraint — parallelism within the drafting swarm will interleave events, and late corrections can append new rows after `RECORD_SET_PACKAGED`.

## 10. Common Pitfalls

- **Don't write the xlsx from Python directly.** The only sanctioned writer is the Excel built-in, fed by the JSON row that `append_audit.py` emits.
- **Don't reuse `event_id`.** Even for "corrections" — always mint a new UUID.
- **Don't pass `before` as a Python dict.** `append_audit.py` expects a JSON string, so skills should `json.dumps(...)` before passing.
- **Don't backdate.** `timestamp_utc` is server-stamped; any caller-supplied value is ignored.

See also:
- `assets/audit-log-template.md` — describes the xlsx template layout.
- `scripts/append_audit.py` — the sole writer.
- `scripts/render_audit_dashboard.py` — the dashboard payload generator.

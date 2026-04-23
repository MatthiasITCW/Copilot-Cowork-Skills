# Audit Log xlsx Template

This file describes the structure the **Excel** built-in should create the first time `scripts/append_audit.py` emits a row for a new RFP. We cannot ship a binary `.xlsx` as an asset in the POC, so this markdown is the authoritative spec — the Excel built-in creates the workbook from this description on demand.

## File Creation Trigger

Trigger: first invocation of `append_audit.py` for a given `<rfp_id>` where `output/rfp-<rfp_id>/audit-log.xlsx` does not yet exist.

Behavior: the Excel built-in creates the workbook per the spec below, writes the header row, applies formatting, then appends the inbound event row as the first data row.

## Workbook Spec

- **Filename:** `audit-log.xlsx`
- **Location:** `output/rfp-<rfp_id>/`
- **Sheets:** exactly one, named `AuditLog`
- **Header row:** row 1 (frozen)
- **Filter:** auto-filter enabled on all 15 columns
- **Column widths:** default auto; no custom widths
- **Number format:** `confidence` column formatted as number with 2 decimal places; all other columns as text

## Header Row (exact order)

| Col | Header |
|---|---|
| A | `event_id` |
| B | `timestamp_utc` |
| C | `rfp_id` |
| D | `skill` |
| E | `event_type` |
| F | `actor` |
| G | `actor_id` |
| H | `target_type` |
| I | `target_id` |
| J | `before` |
| K | `after` |
| L | `reason` |
| M | `provenance_id` |
| N | `confidence` |
| O | `notes` |

## Sample Seed Row (first data row, illustrative only)

| event_id | timestamp_utc | rfp_id | skill | event_type | actor | actor_id | target_type | target_id | before | after | reason | provenance_id | confidence | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `[PLACEHOLDER-UUID]` | `[PLACEHOLDER-ISO8601]` | `[PLACEHOLDER-RFP-ID]` | `rfp-intake` | `RFP_INTAKE_STARTED` | `ai` | `[PLACEHOLDER-AGENT-ID]` | `question` | `[PLACEHOLDER-Q-ID]` | `null` | `{"status":"parsing"}` | | `[PLACEHOLDER-SOURCE]` | | `first event for this RFP` |

## Notes for Implementers

- The Excel built-in must **preserve** the header row on every append — only data rows (row 2+) are written by downstream events.
- No formulas are written into the sheet; all analytics are computed by `scripts/render_audit_dashboard.py`.
- If the workbook exists but the `AuditLog` sheet does not, treat this as corruption and fail loudly rather than auto-repairing.

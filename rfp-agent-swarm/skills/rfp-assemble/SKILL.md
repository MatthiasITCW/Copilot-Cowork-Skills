---
name: rfp-assemble
description: |
  Step 6 of the RFP Agent Swarm. Assembles the approved, gate-passed, reviewed
  responses into the buyer's required format (Word narrative, Excel questionnaire,
  PDF flattened, or portal CSV/JSON for Ariba / Coupa / Jaggaer), applies company
  branding, attaches the cover letter, and generates a companion analytics report
  covering match rate, confidence distribution, gate outcomes, effort metrics, and
  full response-level provenance.
  Use when user says "assemble the RFP response", "build the submission package",
  "generate RFP deliverable", "finalize RFP", "create analytics report",
  "package the RFP for submission", "produce the final deliverable",
  "compile RFP answers into the submission format", "generate the buyer-format
  response", "assemble the bid", or needs the approved responses turned into a
  branded, traceable submission package ready for the deal lead to submit.
---

# RFP Assemble

Take the reviewed, gate-passed responses from `rfp-review` and produce a branded,
buyer-format submission package, a cover letter, and an analytics report — with
full provenance embedded so every answer traces back to a KB source or a
`generated+reviewed` record.

## 1. When to Use

Use `rfp-assemble` **after** `rfp-review` has signed off every response and
`rfp-gates` has marked all three mandatory gates (Security Completeness,
Legal Review, Pricing Approval) as Approved. Typical phrasings: "assemble
the RFP response", "build the submission package", "finalize the RFP",
"create the analytics report for exec review", "produce the buyer-format
deliverable", "assemble the bid".

### Do NOT use for…

Parsing / classifying incoming RFP → `rfp-intake`. Bid / no-bid decision →
`rfp-fit-assessment`. Drafting individual responses → `rfp-respond`. Running
the three quality gates → `rfp-gates`. Human review of flagged items →
`rfp-review`. Adding corrections to the knowledge base → `rfp-answer-bank`.
Raw file rendering from a manifest → built-in `docx` / `xlsx` / `pdf`.

If any gate is not Approved, or any response is still flagged for review,
**stop** and hand control back to `rfp-gates` or `rfp-review`. This skill
never assembles unapproved content.

---

## 2. Inputs and Outputs

### Required inputs

| Input | Source |
|:---|:---|
| Reviewed responses (JSON) | `rfp-review` |
| Gate audit log (JSON) | `rfp-gates` |
| Corrections log (JSON) | `rfp-review` |
| RFP metadata (JSON: buyer, ID, due date, required format, page limits) | `rfp-intake` |
| Branding config | `assets/branding-guide.md` + org-supplied token file |
| Cover letter template | `assets/cover-letter-template.md` |

### Produced outputs

| Output | File |
|:---|:---|
| Buyer-format submission | `working/assembled.docx` / `.xlsx` / `.pdf` / `.csv` |
| Cover letter | `working/cover_letter.pdf` |
| Analytics report | `working/analytics_report.docx` or `.pptx` |
| Packaged zip | `output/submission_package.zip` |
| Final dashboard | `mcp__core__render_ui` call |

---

## 3. Workflow Overview

```
  Reviewed + Gate + Corrections + Metadata
                    |
                    v
          assemble_document.py  (emits manifest JSON)
                    |
      +-------------+-------------+
      v             v             v
   docx skill    xlsx skill    pdf skill
      +-------------+-------------+
                    |
                    v
        generate_analytics_report.py
                    |
                    v
           package_submission.py
                    |
                    v
              render-ui dashboard
```

---

## 4. Step-by-Step Procedure

### Step 1. Pre-flight checks

Verify: every question has a reviewed response; all three gates show
`status: Approved`; no response is `pending` or `flagged`; `required_format`
is known; branding tokens are present. On failure, emit a structured error
record and halt — never attempt partial assembly.

### Step 2. Choose deliverable format

See `references/deliverable-formats.md`. Short version: Word template →
`word`; Excel questionnaire → `excel`; read-only / signed submission → `pdf`;
Ariba / Coupa / Jaggaer portal → `portal` (CSV / JSON / XML); no template →
`word` (default).

### Step 3. Build the manifest

```
python scripts/assemble_document.py \
  --responses working/reviewed_responses.json \
  --format <word|excel|pdf|portal> \
  --template <template_path> \
  --output working/assembled_manifest.json
```

The manifest describes sections, ordering, content blocks, style hints, cover
letter path, and the provenance appendix. It does **not** write Word / Excel /
PDF bytes — those come from the built-in skills.

### Step 4. Render the submission file

Invoke the appropriate built-in skill against `assembled_manifest.json`:
Word narrative → `docx`; Excel questionnaire → `xlsx`; flattened PDF → `pdf`
(or Word → PDF); portal CSV / JSON / XML → direct stdlib write.

### Step 5. Populate cover letter

Read `assets/cover-letter-template.md`, substitute placeholders from RFP
metadata, then render via the `pdf` skill to `working/cover_letter.pdf`.

### Step 6. Generate analytics report

```
python scripts/generate_analytics_report.py \
  --responses working/reviewed_responses.json \
  --gate-audit working/gate_audit.json \
  --corrections working/corrections.json \
  --metadata working/rfp_metadata.json \
  --output working/analytics_report.json
```

Then render via `docx` (read-only report) or `pptx` (exec deck) using the
structure in `references/analytics-report-template.md`.

### Step 7. Package the submission

```
python scripts/package_submission.py \
  --assembled working/assembled.docx \
  --cover-letter working/cover_letter.pdf \
  --analytics working/analytics_report.docx \
  --attachments working/attachments/*.pdf \
  --output output/submission_package.zip
```

### Step 8. Delivery gate

After packaging, the skill caller **must** run
`Glob output/submission_package.zip` to confirm the artefact exists. Never tell
the user "done" unless the file is present on disk.

### Step 9. Final dashboard

Call `mcp__core__render_ui` with submission status (ready yes/no), package
checksum and size, links to all artefacts, and a summary of match rate, gate
outcomes, and SME hours saved.

---

## 5. Deliverable Format Summary

See `references/deliverable-formats.md`. Key rules: **Word** — Cover letter →
Exec summary → Company overview → Technical → Security → Commercial →
Appendices → Provenance appendix. **Excel** — one sheet per category, one row
per question, provenance as extra columns. **PDF** — same ordering as Word,
flattened, locked, signed footer. **Portal CSV** — columns per buyer spec
(Ariba / Coupa / Jaggaer), provenance metadata sidecar file.

---

## 6. Branding

See `references/branding-guide.md`. Branding tokens live in a JSON file
supplied by the organisation. The skill never hard-codes colours or fonts.
Tokens cover typography (heading scale, body font), colour palette (heading
accent, table banding, chart colours), logo (cover, header, footer), and
footer text (legal name, registration, confidentiality marker). Applied
consistently across cover letter, submission file, and analytics report.

---

## 7. Analytics Report

See `references/analytics-report-template.md`. Sections: exec summary, match
rate breakdown (HIGH / MEDIUM / LOW), confidence donut, gate outcomes, effort
metrics (SME hours saved), learning-loop stats, provenance audit, trend
comparison vs prior RFPs. All arithmetic lives in
`scripts/generate_analytics_report.py` — never rely on the LM for numeric
aggregation.

---

## 8. Provenance

See `references/provenance-tracking.md`. Every assembled response carries:
`response_id`, `question_id`, `source` (`bank_entry:KB-0925` or
`generated+reviewed`), `tier` (HIGH / MEDIUM / LOW), `reviewer`,
`review_status`, `last_updated` (ISO-8601).

Embedding per format: Word — appendix + Word comments on tricky answers;
Excel — extra columns per row; PDF — flattened appendix; Portal CSV —
side-car `manifest.json` with the ZIP.

**Audit requirement**: provenance appendix row count must equal the total
question count. `assemble_document.py` fails the build if they disagree.

---

## 9. Troubleshooting

| Symptom | Fix |
|:---|:---|
| `missing_reviewed_response` | Re-run `rfp-review` for that question; never skip |
| `provenance_appendix_mismatch` | Check for duplicate or dropped records in reviewed responses JSON |
| Gate audit shows `rejected` | Return to `rfp-gates`; assemble cannot run with a rejection |
| Analytics `NaN` match rate | Validate every row has a `tier` field |
| Cover letter shows `[BUYER_NAME]` | Ensure RFP metadata has `buyer_name`; re-render |
| Excel missing provenance columns | Re-run `assemble_document.py --format excel` |
| Portal CSV rejected by Ariba | Use UTF-8 with BOM; see deliverable-formats.md Ariba section |
| Zip missing analytics report | Re-run analytics step before packaging |
| Final file not in `output/` | Run `Glob output/**`; re-run packaging if absent |

---

## 10. Built-In Skills Used

| Cowork Skill | How this skill uses it |
|:---|:---|
| Word | Narrative deliverable, cover letter body, long-form analytics report |
| Excel | Questionnaire deliverable (one sheet per category), audit log workbook |
| PDF | Flattens deliverable, renders cover letter, stamps disclaimer footer |
| PowerPoint | Executive analytics deck when leadership wants a slide summary |
| Adaptive Cards | Pre-assembly confirm, record-set manifest, analytics teaser, Ready-to-Submit cards |
| Email | Optional notification that the record set is ready for submission |
| Communications | Internal announcement that the submission package is ready |
| Deep Research | Provenance verification for flagged items with ambiguous KB trace |
| Enterprise Search | Locates prior record sets for the same buyer for trend comparison |

---

## 11. Audit Log

Every step of assembly writes a structured event to
`output/rfp-<rfp_id>/audit-log.xlsx`. The audit log is itself included as an
artefact inside the final record set (see section 12).

| Event Type | When | Actor | Key fields |
|:---|:---|:---|:---|
| `ASSEMBLY_STARTED` | Skill begins assembly | AI | `rfp_id`, `target_format` (Word/Excel/PDF/Portal) |
| `FORMAT_SELECTED` | Buyer format locked in | AI | `format`, `reason`, `template_ref` |
| `DELIVERABLE_GENERATED` | Main deliverable written | AI | `format`, `file_path`, `question_count`, `provenance_appendix_count` |
| `ANALYTICS_COMPUTED` | Analytics report computed | AI | `match_rate`, `tier_distribution`, `gate_stamps`, `sme_hours_saved` |
| `RECORD_SET_PACKAGED` | Final record set zipped | AI | `record_set_path`, `artefact_count`, `sha256` |

Events are appended via the shared helper:
[audit-log-schema.md](../rfp-answer-bank/references/audit-log-schema.md)
(full schema) and
[append_audit.py](../rfp-answer-bank/scripts/append_audit.py) (append
helper). The audit log is **included as an artefact IN the record set**
(artefact #10) — a single zip contains both the submission and the full
trace of how it was built.

---

## 12. Record Set

The output of `rfp-assemble` is **not a single document** — it is a **RECORD
SET**: a cohesive, inspectable, durable collection of every artefact
produced during the RFP lifecycle. This is what makes the swarm auditable
end-to-end.

### Manifest of artefacts

| # | Artefact | Format | Source skill | Purpose |
|:--:|:---|:---|:---|:---|
| 1 | Original RFP source document(s) | Word / PDF / Excel | `rfp-intake` input | Provenance — what was submitted to us |
| 2 | Extracted question bank | Excel | `rfp-intake` | Normalised question list, classifications, mandatory flags |
| 3 | Fit assessment memo | Word | `rfp-fit-assessment` | Go / No-Go rationale, scorecard, human decision |
| 4 | Drafted responses with provenance | Excel | `rfp-respond` | Every answer tagged with KB source or `generated+reviewed` |
| 5 | Gate audit trail | Excel (subset of audit log) | `rfp-gates` | Each gate request / approval / rejection with approver + timestamp |
| 6 | Corrections log | Excel | `rfp-review` | Every human correction with before / after + reason taxonomy |
| 7 | Buyer-format submission deliverable | Word / Excel / PDF / Portal CSV | `rfp-assemble` | The actual response we send to the buyer |
| 8 | Cover letter | PDF | `rfp-assemble` | Formal transmittal letter |
| 9 | Analytics report | Word or PowerPoint | `rfp-assemble` | Match rate, confidence distribution, SME hours saved, provenance audit |
| 10 | Audit log | Excel | `rfp-answer-bank` (shared) | End-to-end event log across all 7 steps |
| 11 | Record set manifest (`manifest.json`) | JSON | `rfp-assemble` | Index of every artefact with sha256 + retention metadata |

### Record set composition (ASCII diagram)

```
            output/rfp-<rfp_id>/  (zipped on packaging)
 +-----------------------------------------------------------+
 |  INPUT PROVENANCE            AUTOMATED PIPELINE OUTPUT    |
 |  [1] original-rfp.*          [4] drafted-responses.xlsx   |
 |  [2] question-bank.xlsx      [5] gate-audit.xlsx          |
 |  [3] fit-memo.docx           [6] corrections-log.xlsx     |
 |                                                           |
 |  ASSEMBLE (this skill) OUTPUT                             |
 |  [7] submission.(docx|xlsx|pdf|csv)                       |
 |  [8] cover-letter.pdf                                     |
 |  [9] analytics-report.(docx|pptx)                         |
 |                                                           |
 |  SHARED / INDEX                                           |
 |  [10] audit-log.xlsx                                      |
 |  [11] manifest.json   <-- index of 1..10                  |
 +-----------------------------------------------------------+
                       |
                       v
       record-set-<rfp_id>.zip   (sha256 recorded in manifest)
```

### Properties of the record set

- **Storage**: all artefacts live in `output/rfp-<rfp_id>/` and are zipped into `record-set-<rfp_id>.zip`.
- **Integrity**: every artefact is sha256-hashed; `manifest.json` records hash, size, author, `created_at`.
- **Retention**: durable record of the RFP's entire lifecycle — kept for the buyer's required retention period (typically **7 years** commercial, **longer** for public-sector).
- **Inspectability**: any stakeholder can trace any answer back to its KB source, reviewer, approver, and timestamp without re-running the pipeline.
- **Self-contained**: includes both the submission *and* the audit log that explains how every byte in the submission was produced.

---

## 13. Adaptive Card Dashboard

Assembly is surfaced to the user through a sequence of Adaptive Cards rendered
via the Cowork **Adaptive Cards** built-in.

| Card | When | Contents |
|:---|:---|:---|
| Pre-assembly confirm | Before Step 1 | Target format (Word / Excel / PDF / Portal), record-set inventory showing current state of artefacts 1–6, CTA "Begin assembly" |
| Record-set manifest | On assembly complete | Table of all 11 artefacts with file sizes; a present / missing badge for each; sha256 summary row |
| Analytics teaser | After Step 6 | KPI row (total questions, match rate, SME hours saved), gate-stamp row (three green/red chips), donut of confidence distribution |
| Ready to Submit (final) | After Step 7 | ALL gate-approved timestamps, package checksum + size, CTA **"Submit to buyer portal"** — which is a **HUMAN action**, never automated |

The "Submit to buyer portal" CTA does **not** trigger an automated upload —
the human deal lead performs the actual submission; the card merely
deep-links to the zip and to the buyer portal URL.

---

## 14. Related Skills

### RFP chain

```
rfp-intake -> rfp-fit-assessment -> rfp-respond -> rfp-gates
          -> rfp-review -> THIS SKILL -> [human submits]
```

This skill is the **terminal step of the automated pipeline**. It consumes
artefacts from every upstream skill and packages them as the record set. A
**human performs the actual submission** to the buyer portal — the swarm never
submits on behalf of the organisation.

| Skill | Relationship |
|:---|:---|
| `rfp-intake` | Supplies RFP metadata (buyer, ID, due date, required format) and artefacts 1–2 |
| `rfp-fit-assessment` | Upstream bid / no-bid; supplies artefact 3; assemble never runs on a no-bid |
| `rfp-respond` | Produces artefact 4 — the candidate responses that become deliverable content |
| `rfp-gates` | All three gates must be Approved before assemble can start; supplies artefact 5 |
| `rfp-review` | Supplies the reviewed, approved response set and artefact 6 (corrections log) |
| `rfp-answer-bank` | Consumes corrections from this RFP to improve future match rates; owns the shared audit log helper |

### Cowork built-ins leveraged

See section 10 for the full mapping: **Word**, **Excel**, **PDF**,
**PowerPoint**, **Adaptive Cards**, **Email**, **Communications**, **Deep
Research**, and **Enterprise Search** are all invoked by this skill during
assembly, packaging, and stakeholder notification.

### Cross-links

Deliverable formats `references/deliverable-formats.md` · Branding
`references/branding-guide.md` · Analytics `references/analytics-report-template.md` ·
Provenance `references/provenance-tracking.md` · Cover letter
`assets/cover-letter-template.md` · Disclaimer `assets/disclaimer-footer.md`

---

**Design note:** this skill treats the final deliverable as a traceable,
auditable record set — not just a document. Every byte either traces to a KB
source or to a logged `generated+reviewed` decision. That is the contract
this skill holds with the wider RFP Agent Swarm.

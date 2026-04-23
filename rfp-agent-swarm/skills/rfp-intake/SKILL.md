---
name: rfp-intake
description: |
  Automated ingestion, parsing, and classification of incoming Request-for-Proposal
  (RFP), RFI, RFQ, tender, bid, and security-questionnaire documents. This skill
  extracts every question, classifies it by team (Security, Technical, Commercial,
  Company, General), detects mandatory vs optional items, extracts buyer metadata
  (deadline, submission format, evaluation criteria, page limits), and produces
  the structured task list that every downstream RFP skill consumes.

  Use when the user says any of:
    - "a new RFP came in, can you parse it"
    - "parse this RFP"
    - "intake this proposal"
    - "classify RFP questions"
    - "extract RFP questions from this document"
    - "log this RFP in our system"
    - "process this tender"
    - "ingest this bid document"
    - "break down this RFP by team"
    - "what's in this RFP, give me the summary"
    - "triage this security questionnaire"
    - "set up the task list for this bid"

  Do NOT use for: making the bid / no-bid decision (route to rfp-fit-assessment),
  drafting answer content (rfp-respond), running quality gates (rfp-gates),
  human review of drafts (rfp-review), final document assembly (rfp-assemble),
  or querying the knowledge base for prior answers (rfp-answer-bank). This skill
  stops the moment a clean task list and intake card exist.

cowork:
  category: sales-proposals
  icon: inbox
---

# RFP Intake — Step 1: Ingest and Parse

The rfp-intake skill is the front door of the RFP Agent Swarm. Every incoming
buyer document lands here first. Its job is narrow and mechanical: turn an
unstructured RFP document into a structured, classified, deduplicated task list
that the specialist teams (Security, Technical, Commercial) can work on in
parallel. It does not write answers, judge fit, or decide bid/no-bid.

Design principles baked in:

- Retrieval over generation — we extract what is in the document, we do not
  invent questions, deadlines, or evaluation criteria.
- Transparency over automation — every classification carries a confidence
  score; low-confidence items are flagged for human triage rather than hidden.
- Safety over speed — if a document cannot be parsed reliably, we stop and
  escalate rather than emit a corrupted task list.
- Parallel over sequential — the output is explicitly structured so Security,
  Technical, and Commercial teams can work at the same time.

## When to Use

- A new RFP, RFI, RFQ, tender, or security questionnaire has arrived by email,
  portal export, or SharePoint drop.
- A buyer has sent a follow-up document with additional questions that must be
  merged into the existing task list.
- A deal lead needs a quick breakdown by team before running the go/no-go.
- A security questionnaire (SIG Lite, CAIQ, VSA, HECVAT) needs to be sliced
  into individual tasks.
- A portal export (Ariba, Coupa, Jaggaer, RFx) needs to be turned into an
  internal workbook.
- The deal lead asks "what's in this RFP" and needs numbers, not prose.

## When NOT to Use

- Bid / no-bid decision, strategic fit, win-theme selection — delegate to
  [rfp-fit-assessment].
- Drafting answer text, querying the knowledge base, or mapping questions to
  evidence artefacts — delegate to [rfp-respond] and [rfp-answer-bank].
- Running the three mandatory quality gates (compliance, accuracy, tone) —
  delegate to [rfp-gates].
- Reviewing, correcting, or approving drafts — delegate to [rfp-review].
- Assembling the final response document or analytics pack — delegate to
  [rfp-assemble].
- Answering a single ad-hoc buyer question with no document attached — that is
  a direct [rfp-answer-bank] lookup.

## Quick Start — Worked Example

Scenario: At 09:14 on 2026-04-22 the deal lead forwards an email from
"Procurement — Northwind Traders" with an attached Word file
`Northwind_RFP_2026_CloudPlatform.docx` and an Excel security tab
`Northwind_SecurityQuestionnaire.xlsx`. Response deadline: 2026-05-20.

1. Drop both files into `input/` and confirm they arrived:
   `ls input/Northwind_*`.
2. Extract the text layer using the `docx` and `xlsx` built-in skills and write
   the plain text to `working/northwind_rfp.txt` and
   `working/northwind_sec.tsv`.
3. Run the raw parser against both extracted files:
   `python scripts/parse_rfp.py working/northwind_rfp.txt --output working/rfp_raw.json`
   then merge the security tab via the same script with `--append`.
4. Run classification:
   `python scripts/classify_questions.py working/rfp_raw.json
   --taxonomy references/question-classification-taxonomy.md
   --output working/classified.json`.
5. Build the task list:
   `python scripts/build_task_list.py --metadata working/rfp_raw.json
   --classifications working/classified.json --output working/task_list.json`.
6. Read the markdown summary the builder wrote to stderr and sanity-check the
   counts against the document's own table of contents.
7. Render the intake Adaptive Card via the render-ui built-in (buyer,
   deadline, totals by category, mandatory count, evaluation criteria).
8. Produce the internal workbook: hand `working/task_list.json` to the xlsx
   built-in skill to emit `output/Northwind_RFP_TaskList.xlsx`.
9. Produce the optional deal-lead briefing via the docx built-in skill using
   [assets/intake-confirmation-template.md](assets/intake-confirmation-template.md).
10. Post the Teams confirmation using the same template and hand off to
    rfp-fit-assessment with a link to `working/task_list.json`.

## Core Instructions and Workflow

The skill runs a strict five-phase pipeline. Each phase produces a durable
artefact so a human can audit or re-run any single phase without replaying the
whole pipeline.

### Phase table

| Phase | Purpose | Primary tool | Output artefact |
|-------|---------|--------------|-----------------|
| 1. Locate | Find the RFP document(s) in `input/`, attachments, or SharePoint | filesystem | path list |
| 2. Extract | Convert Word / Excel / PDF to plain text or TSV | docx / xlsx / pdf | `working/*.txt`, `*.tsv` |
| 3. Parse | Detect sections, buyer block, deadlines, raw questions | [scripts/parse_rfp.py](scripts/parse_rfp.py) | `working/rfp_raw.json` |
| 4. Classify | Assign category, owner team, mandatory flag, confidence | [scripts/classify_questions.py](scripts/classify_questions.py) | `working/classified.json` |
| 5. Assemble | Merge into the canonical task list | [scripts/build_task_list.py](scripts/build_task_list.py) | `working/task_list.json` |

### Category routing

Each question is routed to exactly one owner team (primary_category). A
secondary_category may also be set when the question legitimately spans two
domains. Full signal lists live in
[references/question-classification-taxonomy.md](references/question-classification-taxonomy.md).

| Category | Owner team | Typical signals |
|----------|-----------|-----------------|
| Security | Security Engineering | SOC 2, ISO 27001, encryption, penetration test, incident response |
| Technical | Solution Architecture | API, SSO, deployment model, latency, SLA target, integration |
| Commercial | Commercial Desk | pricing, payment terms, SLA credits, discount, MSA, term length |
| Company | Corporate Marketing | years in business, references, financial stability, DE&I |
| General | Bid Manager | submission format, point of contact, proposal template, schedule |

### Mandatory vs optional

A question is flagged mandatory when the sentence contains any of "must",
"shall", "is required", "is mandatory", or is explicitly tagged "(M)" in a
questionnaire template. It is flagged optional on "may", "nice to have",
"optional", "(O)". Anything ambiguous defaults to mandatory — the bias is
toward over-answering, never under-answering. Full pattern list is in
[references/question-classification-taxonomy.md](references/question-classification-taxonomy.md).

### Parsing confidence

The parser emits one of three confidence levels, defined in
[references/parsing-playbook.md](references/parsing-playbook.md):

| Level | Meaning | Action |
|-------|---------|--------|
| HIGH | Every question has an extracted ID and text, totals match the TOC | Auto-proceed to classify |
| MEDIUM | Most questions extracted, some tables irregular | Human spot-check before classify |
| LOW | Document format too irregular or scanned with poor OCR | Stop, escalate to human intake, do not emit a task list |

### Schema discipline

The RFP metadata record and question schema are defined in
[references/rfp-metadata-schema.md](references/rfp-metadata-schema.md). Every
downstream skill assumes this exact shape. Do not invent new fields; if a
buyer supplies information that does not fit, add it to `notes` on the
question or under `custom_fields` on the RFP record.

### Calculations

Do not do mental arithmetic on counts, percentages, effort estimates, or
deadline math. All counts come from `build_task_list.py`'s structured output;
all date math runs through Python's stdlib `datetime`.

## Built-In Skills Used

| Cowork Skill | How this skill uses it |
|--------------|------------------------|
| Word | Extract text from buyer-supplied Word RFPs; emit the optional deal-lead briefing |
| Excel | Extract question rows from multi-tab questionnaire workbooks; emit the internal task-list workbook; append rows to the shared audit log |
| PDF | Extract text layer (or OCR) from PDF RFPs and portal exports |
| Adaptive Cards | Render the inline intake summary dashboard for the deal lead in Copilot chat |
| Enterprise Search | Look up buyer background, prior RFPs on file, and prior interactions; does not fetch answers (that is rfp-answer-bank) |
| Email | Fetch the original buyer email and attachments from the shared bid mailbox; send an optional confirmation back to the submitter |

Out of scope for this skill: Deep Research, Calendar Management, Scheduling,
Meetings, Communications, PowerPoint. Those belong to downstream skills.

## Output Deliverables

| Deliverable | Consumer | Built-in skill used |
|-------------|----------|---------------------|
| `working/rfp_raw.json` | internal pipeline | scripts only |
| `working/classified.json` | internal pipeline | scripts only |
| `working/task_list.json` | rfp-fit-assessment, rfp-respond | scripts only |
| Inline intake Adaptive Card | deal lead in Copilot chat | render-ui |
| `output/<rfp_id>_TaskList.xlsx` | bid manager, specialist teams | xlsx |
| `output/<rfp_id>_Briefing.docx` (optional) | deal lead | docx |
| Teams / email confirmation | deal team | Email, plus [assets/intake-confirmation-template.md](assets/intake-confirmation-template.md) |

## Audit Log

This skill writes events to the shared RFP audit log at
`output/rfp-<rfp_id>/audit-log.xlsx`. Rows are appended via the Excel built-in;
the schema and the writer are owned by rfp-answer-bank, which guarantees all
seven RFP skills share a single consistent chain of custody.

| Event Type | When it fires | Actor | Key fields captured |
|------------|---------------|-------|---------------------|
| RFP_INTAKE_STARTED | Skill begins parsing a new RFP | AI | rfp_id, source_filename, buyer |
| QUESTION_EXTRACTED | Each question pulled from the doc | AI | question_id, section, raw_text |
| CLASSIFICATION_APPLIED | Each question tagged by team | AI | question_id, team, confidence |
| TASK_LIST_CREATED | Task list for downstream teams generated | AI | total_questions, per_team_counts |
| INTAKE_COMPLETE | All parsing finished | AI | rfp_id, total_questions, deadline, mandatory_format |

State: rows are appended via the Excel built-in; the schema and writer are
owned by rfp-answer-bank. See
[audit-log-schema.md](../rfp-answer-bank/references/audit-log-schema.md) for
the column definitions and
[append_audit.py](../rfp-answer-bank/scripts/append_audit.py) for the shared
writer helper.

## Adaptive Card Dashboard

At intake completion the skill renders an inline dashboard via the Adaptive
Cards built-in so the deal lead gets a single glanceable summary before
go/no-go. The card is composed of these elements, in order:

- KPI row — total questions, per-team counts (Security / Technical /
  Commercial / Company / General), mandatory vs optional split, and
  days-to-deadline.
- Donut chart — questions by team, colour-coded to the owner team.
- FactSet — buyer name, RFP ID, deadline, submission format, evaluation
  criteria (top 5, truncated if longer).
- Table — first 10 questions with columns for question ID, section, owner
  team, and a mandatory badge.
- Call-to-action — a prominent link-style action reading
  "Ready to run the go/no-go assessment?" that hands the deal lead off to
  rfp-fit-assessment with `working/task_list.json` attached.

The full question set, full evaluation criteria, and full metadata record
always stay in `output/<rfp_id>_TaskList.xlsx`; the card is a summary, not
the system of record.

## Guardrails

- Never invent a question, deadline, buyer name, or evaluation criterion that
  is not literally present in the source document. Retrieval over generation.
- Never make the bid / no-bid decision in this skill. If asked, hand off to
  rfp-fit-assessment with the intake artefacts attached.
- Never generate pricing, pricing commentary, or commercial positioning.
  Commercial questions are tagged and routed; their answers are out of scope.
- Never fabricate certifications. If a question asks about ISO 27001 and the
  system does not already have that certification on file, the task is routed
  to Security Engineering for verification, not auto-answered.
- Never overwrite a prior `working/task_list.json` in place. Always write a
  new file with an incrementing suffix so the audit trail survives re-runs.
- Stop and escalate if parsing confidence is LOW. Do not emit a partial or
  guessed task list.
- Do not send external communications from this skill. Buyer replies, clocks,
  and commitments are the deal lead's responsibility.

## Common Issues

| Symptom | Likely cause | Resolution |
|---------|--------------|------------|
| `parse_rfp.py` returns zero questions | Scanned PDF with no text layer | Run PDF skill OCR first, then re-parse; if still zero, mark LOW confidence |
| Question counts do not match RFP's own TOC | Parser missed a table variant | Re-run with `--table-mode strict`; inspect `parse_log` in stderr |
| Everything classified as "General" | Taxonomy signal lists not loaded | Confirm `--taxonomy` points at the real file; check file exists and is non-empty |
| Security questionnaire sub-questions collapsed into one | Nested bullets flattened | Use the xlsx extractor instead of docx; each row becomes one question |
| Deadline extracted as today's date | Buyer block used "issued" wording, not "due" | Check `deadline_candidates` array; pick the one tagged `due` / `response due` |
| Portal export CSV has ID column but no text | Wrong column mapping | Pass `--id-column` and `--text-column` explicitly to the parser |
| Duplicate questions across tabs | Buyer copy-pasted boilerplate between tabs | `build_task_list.py` dedupes by normalised-text hash; check `duplicates_removed` counter |
| Adaptive Card exceeds Teams size limit | Too many evaluation criteria inlined | Card truncates to top 5; full list stays in the xlsx workbook |

## Related Skills

This skill is one of seven siblings in the RFP Agent Swarm. Handoffs are
explicit and carry the artefacts listed above:

- [rfp-fit-assessment] — consumes `working/task_list.json` and the intake card
  to run the go/no-go decision (human + AI). Next step after rfp-intake.
- [rfp-respond] — consumes the task list and fans out to Security, Technical,
  and Commercial drafting agents in parallel.
- [rfp-answer-bank] — queried by rfp-respond against the Loopio export in
  Azure AI Search; rfp-intake only checks it for "have we seen this buyer
  before". Also owns the shared audit-log schema and writer.
- [rfp-gates] — runs the three mandatory quality gates after drafting.
- [rfp-review] — captures human corrections and feeds them back to the
  answer bank.
- [rfp-assemble] — builds the final submission document and analytics pack.

### RFP chain (where this sits)

```
rfp-intake -> rfp-fit-assessment -> rfp-respond -> rfp-gates -> rfp-review -> rfp-assemble
                                           |
                                           +-- rfp-answer-bank (shared substrate)
```

rfp-intake is the entry point of the chain. Every buyer document lands here
first. Once parsing, classification, and task-list assembly are complete,
rfp-intake hands the question list (`working/task_list.json`) plus the
intake Adaptive Card off to rfp-fit-assessment, which runs the go/no-go.
rfp-answer-bank sits underneath the whole chain as shared substrate: it owns
the canonical audit log, the Loopio knowledge-base index, and the reusable
event writer helpers that every RFP skill calls.

### Cowork built-ins leveraged

- Word — read `.docx` RFPs via the Word built-in.
- Excel — read `.xlsx` security questionnaires; append audit log rows.
- PDF — read `.pdf` RFPs and portal exports.
- Adaptive Cards — render the intake summary dashboard described above.
- Enterprise Search — look up buyer background and prior interactions.
- Email — optional confirmation back to the submitter.

See also: [references/question-classification-taxonomy.md](references/question-classification-taxonomy.md),
[references/rfp-metadata-schema.md](references/rfp-metadata-schema.md),
[references/parsing-playbook.md](references/parsing-playbook.md),
[assets/intake-confirmation-template.md](assets/intake-confirmation-template.md),
`python scripts/parse_rfp.py`, `python scripts/classify_questions.py`,
`python scripts/build_task_list.py`.

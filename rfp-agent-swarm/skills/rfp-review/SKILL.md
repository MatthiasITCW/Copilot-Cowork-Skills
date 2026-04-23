---
name: rfp-review
description: Step 5 of the RFP agent swarm. Surfaces only the flagged items that need human attention, captures every reviewer correction with a structured reason, and feeds the learning loop that improves the answer bank for future RFPs.
triggers:
  - "review flagged RFP items"
  - "human review"
  - "correct RFP responses"
  - "capture corrections"
  - "review low-confidence answers"
  - "walk me through flagged items"
  - "start reviewer queue"
  - "log this correction"
  - "fix this RFP answer"
  - "approve the flagged responses"
---

# rfp-review — Human Review and Correction Capture

Step 5 in the RFP workflow (after `rfp-gates`, before `rfp-assemble`). This skill exists because transparency over automation is a design principle: every HIGH-confidence auto-answer is audited and every LOW-confidence or generated answer is seen by a human before the package ships.

More importantly, this is where the **learning loop** closes. Every correction a reviewer makes is logged with a structured reason, and that correction is what makes the next RFP easier. No correction capture, no learning.

## 1. When to use this skill

Use `rfp-review` when:

- `rfp-respond` has produced a `responses.json` with mixed confidence tiers
- `rfp-gates` has produced a `gate_verdict.json` with FAIL or WARN items
- A reviewer needs a triaged queue instead of scrolling 300 raw answers
- A reviewer has made a correction and it needs to be logged for the learning loop
- You need to export accumulated corrections into a payload that `rfp-answer-bank.merge_corrections` can consume

### Do NOT use for

- **Drafting answers** — that is `rfp-respond`.
- **Compliance gating** — that is `rfp-gates`. This skill consumes gate output, it does not produce it.
- **Building the final deliverable** — that is `rfp-assemble`.
- **Editing the KB directly** — corrections captured here are *proposals*. Merge happens in `rfp-answer-bank`.
- **Bulk re-answering** — if more than ~40% of responses are flagged, go back to `rfp-respond` and fix the retrieval step.

## 2. The learning loop (why this skill matters)

```
  +--------------------+     +---------------------+     +------------------+
  |  rfp-respond       | --> |  rfp-gates          | --> |  rfp-review      |
  |  (drafts answers)  |     |  (flags violations) |     |  (THIS SKILL)    |
  +--------------------+     +---------------------+     +--------+---------+
                                                                  |
                                                                  | reviewer
                                                                  | corrects
                                                                  v
                                                          +----------------+
                                                          | corrections.   |
                                                          | jsonl          |
                                                          | (append-only)  |
                                                          +-------+--------+
                                                                  |
                                                                  | export_corrections.py
                                                                  v
                                                          +----------------+
                                                          | rfp-answer-    |
                                                          | bank           |
                                                          | merge_         |
                                                          | corrections    |
                                                          +-------+--------+
                                                                  |
                                                                  | next RFP:
                                                                  | - higher match rate
                                                                  | - lower flag rate
                                                                  | - faster turnaround
                                                                  v
                                                          (back to rfp-respond)
```

Every correction carries: original response, corrected response, reason (from the taxonomy), confidence delta, reviewer email, timestamp, question id, category. Without that structured reason, the merge step cannot decide whether to *replace* a KB entry, *add a sibling*, *retire* an entry, or *no-op*.

## 3. Inputs and outputs

| Input                                 | Source skill     | Required | Purpose                                      |
|---------------------------------------|------------------|----------|----------------------------------------------|
| `responses.json`                      | rfp-respond      | Yes      | All drafted answers with confidence tiers    |
| `gate_verdict.json`                   | rfp-gates        | Yes      | FAIL/WARN items from compliance gating       |
| `rfp_metadata.json`                   | rfp-intake       | Yes      | Buyer context, category map, reviewer roster |
| `answer_bank_freshness.json`          | rfp-answer-bank  | Optional | Per-entry staleness signal                   |

| Output                              | Consumer              | Shape               |
|-------------------------------------|-----------------------|---------------------|
| `working/review_queue.json`         | reviewer UI           | Ordered array       |
| `working/corrections.jsonl`         | rfp-answer-bank       | Append-only JSONL   |
| `working/corrections_export.json`   | merge_corrections.py  | Rolled-up JSON      |
| render-ui queue card                | the reviewer          | Sortable table + KPI row |
| xlsx corrections log                | audit + SME round-up  | Excel workbook      |

## 4. Review queue prioritisation

The queue is built by `scripts/build_review_queue.py`. Priority rank (1 = see first):

| Rank | Condition                                              | Rationale                                     |
|------|--------------------------------------------------------|-----------------------------------------------|
| 1    | Gate verdict = FAIL                                    | Blocks the entire pipeline. Fix or withdraw. |
| 2    | Confidence tier = LOW, or source = GENERATED           | Always human-checked, no exceptions.         |
| 3    | Confidence = MEDIUM with delta-from-source > 0.35      | Significant adaptation — verify facts.       |
| 4    | Mandatory question with no response                    | Missing mandatories = disqualification.      |
| 5    | Category in {Security, Legal, Pricing, Compliance}     | Sensitive regardless of confidence.          |
| 6    | Gate verdict = WARN                                    | Reviewable but not blocking.                 |

HIGH-confidence, non-sensitive, fresh (≤ 90 days) responses **do not enter the queue** unless the reviewer requests an audit pass. They are tagged `review_status: auto-approved` for audit trail.

## 5. Correction taxonomy

See `references/correction-taxonomy.md` for full detail. Summary:

| Reason                       | One-line definition                                                    | KB action on merge      |
|------------------------------|------------------------------------------------------------------------|-------------------------|
| FACTUAL_ERROR                | Answer contained a wrong fact; gold answer now documented              | replace                 |
| OUTDATED_SOURCE              | KB entry was stale; new version provided                               | replace                 |
| TONE_OR_STYLE                | Rewording only, no fact change                                         | no-op (logged)          |
| MISSING_CONTEXT              | Answer correct but lacked buyer-specific context                       | add-sibling             |
| CATEGORY_MISCLASSIFICATION   | Question was routed to the wrong team                                  | reclassify              |
| UNANSWERABLE_FROM_KB         | Genuinely new question; SME answer added                               | add-new                 |
| POLICY_UPDATE                | Company position has changed; old KB entry retired                     | retire + add-new        |
| COMPLIANCE_NUANCE            | Standard answer needed jurisdiction-specific adjustment                | add-sibling             |

Reviewers pick the *most specific* reason. `log_correction.py` validates the enum and refuses unknown values.

## 6. Reviewer workflow

1. Reviewer runs `build_review_queue.py` (or opens the render-ui card).
2. Queue is rendered as a sortable table. KPI row shows counts by priority and by reviewer.
3. For each item, reviewer picks an action:
   - **approve-as-is** — tags `review_status: reviewed`, no correction logged.
   - **approve-with-minor-tone-edit** — logs a `TONE_OR_STYLE` correction.
   - **rewrite** — prompts for a reason from the taxonomy; logs the correction.
   - **reject-and-flag-for-SME** — moves item to SME queue with optional reason.
4. Corrections stream to `working/corrections.jsonl` via `log_correction.py`.
5. When the batch is closed, `export_corrections.py` rolls up the JSONL into a payload for `rfp-answer-bank`.

### Approval shortcuts

| Shortcut                          | Result                                                      |
|-----------------------------------|-------------------------------------------------------------|
| `a` (approve)                     | `review_status: reviewed`, no correction                    |
| `t` (tone edit)                   | Logs `TONE_OR_STYLE`, prompts for corrected text            |
| `r` (rewrite)                     | Prompts for corrected text AND taxonomy reason              |
| `s` (send to SME)                 | Flags item, removes from reviewer's personal queue          |
| `?` (defer)                       | Keeps status quo, re-queues for the next session            |

## 7. Auto-escalation and audit rules

- If a reviewer modifies an answer by more than 120 characters AND selects `TONE_OR_STYLE`, the script auto-reclassifies as `FACTUAL_ERROR` and requires confirmation. This prevents silent factual edits from being logged as cosmetic.
- Every response object in the final `responses_for_assembly.json` must carry a `review_status` field set to one of: `reviewed`, `auto-approved`, `skipped`. `rfp-assemble` rejects any response missing this field.
- Corrections are append-only. Edits to a previously-logged correction must be a new JSONL line with `supersedes: <prior_correction_id>`.

## 8. Commands

```bash
# Build the queue
python scripts/build_review_queue.py \
  --responses working/responses.json \
  --gate-results working/gate_verdict.json \
  --output working/review_queue.json

# Log a correction
python scripts/log_correction.py \
  --question-id Q-0142 \
  --original working/responses.json \
  --corrected "We retain PII for 30 days, not 90." \
  --reason FACTUAL_ERROR \
  --reviewer jdoe@acme.com \
  --appendto working/corrections.jsonl

# Export for the learning loop
python scripts/export_corrections.py \
  --input working/corrections.jsonl \
  --output working/corrections_export.json \
  --since 2026-01-01
```

## 9. Troubleshooting

| Symptom                                                          | Likely cause                                                   | Fix                                                                         |
|------------------------------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------|
| Queue is empty but you expected flagged items                    | `gate_verdict.json` path wrong or verdict = PASS for all items | Re-check path; confirm gates actually ran on this response set              |
| `log_correction.py` refuses with `UnknownReason`                  | Reason not in the enum                                         | Pick from taxonomy; see `references/correction-taxonomy.md`                 |
| Same correction logged twice                                     | Idempotency relies on question_id + reviewer + corrected_hash   | Re-run — duplicates are dropped silently                                    |
| Reviewer fatigue: batch is > 80 items                            | Queue not sharded by team                                      | Use `--filter-category` on `build_review_queue.py` to split by team         |
| `export_corrections.py` emits zero records                       | `--since` date is after the latest correction                  | Lower the date window or omit `--since`                                     |
| `review_status` missing in assembly input                        | Responses bypassed the queue AND were not tagged auto-approved  | Run `build_review_queue.py` with `--tag-auto-approved` to fix the status    |
| 120-char auto-reclassification firing on legitimate tone edits   | Threshold too aggressive for long answers                      | Acceptable — the reviewer confirms; no silent reclass                       |
| Corrections export blocks merge_corrections                      | JSONL contains a malformed line                                | `export_corrections.py` logs the offending line number to stderr; fix it    |

## Built-In Skills Used

| Cowork Skill | How this skill uses it |
|--------------|------------------------|
| Adaptive Cards | Renders the review queue card, per-item review cards, before/after diff preview, and end-of-review summary card |
| Excel | Appends rows to `output/rfp-<rfp_id>/audit-log.xlsx`; exports the corrections log as an xlsx workbook for SME round-up |
| Enterprise Search | Looks up prior answers, source documents, and KB entries when a reviewer challenges a drafted response |
| Communications | Notifies the assigned reviewer that a queue is ready; sends the thank-you summary and learning-loop recap when the batch closes |

## Audit Log

All reviewer activity is written to `output/rfp-<rfp_id>/audit-log.xlsx` via the Excel built-in. Append logic lives in [append_audit.py](../rfp-answer-bank/scripts/append_audit.py) and the row schema is defined in [audit-log-schema.md](../rfp-answer-bank/references/audit-log-schema.md).

| Event Type | When | Actor | Key fields |
|------------|------|-------|------------|
| REVIEW_QUEUE_BUILT | Skill assembles the prioritized queue | AI | rfp_id, queue_size, low_tier_count, generated_count, gate_correction_count |
| CORRECTION_CAPTURED | Reviewer edits an answer | human | question_id, before (original response+tier+source), after (corrected response+new_source), reviewer_id |
| CORRECTION_REASON_TAGGED | Reason code applied | human | question_id, reason_code, taxonomy_branch |
| REVIEW_COMPLETE | All queued items resolved | human | total_reviewed, total_corrected, acceptance_rate |

Note: `CORRECTION_CAPTURED` events also feed the corrections merge into `rfp-answer-bank` — this is the hand-off that closes the learning loop. Every row written here becomes a candidate KB update on the next `merge_corrections` run.

## Adaptive Card Dashboard

All reviewer-facing UI is rendered through the Adaptive Cards built-in. There is no separate web app; the cards are the UI.

- **Review queue card** — KPI row across the top showing total flagged, LOW-tier count, generated count, and gate-correction count. Below the KPI row, filter chips let the reviewer narrow by team, tier, or reason.
- **Per-item review card** — shows the question, the current response with a source/tier badge, an inline edit field for the corrected text, a reason dropdown wired to the correction taxonomy, and three action buttons: Approve, Correct, Escalate.
- **Before/after diff preview card** — rendered on correction submit. Shows the original response on the left and the edited response on the right with word-level diff highlighting so the reviewer can confirm before committing.
- **End-of-review summary card** — shown once the queue is empty. Reports corrections logged, estimated match-rate lift for the next RFP (based on reason-code mix), and a CTA button: "Merge corrections into the answer bank" which triggers `rfp-answer-bank.merge_corrections`.

## 10. Related skills

- **rfp-respond** — produces the draft answers this skill reviews. Check its `tier_threshold` if too many items land in LOW.
- **rfp-gates** — produces the compliance verdict consumed here. Gate rules live in that skill, not this one.
- **rfp-answer-bank** — consumes `corrections_export.json` via its `merge_corrections.py`. The learning loop only works if that skill runs periodically.
- **rfp-assemble** — consumes the reviewed responses. Will refuse items without `review_status`.
- **rfp-intake** — owns the reviewer roster and category map used for `suggested_reviewer`.
- **Excel** (Cowork built-in) — used by `export_corrections.py` for the Excel audit log and the corrections export workbook.
- **Adaptive Cards** (Cowork built-in) — used to display the queue, per-item review UI, diff preview, and summary card.
- **Enterprise Search** (Cowork built-in) — used to pull source documents and prior KB entries when a reviewer challenges a response.
- **Communications** (Cowork built-in) — used to notify the reviewer when the queue is ready and to send the end-of-review summary.

### RFP chain

```
rfp-intake → rfp-fit-assessment → rfp-respond → rfp-gates → THIS SKILL → rfp-assemble
                                       (rfp-answer-bank as substrate throughout)
```

THIS SKILL is the bridge between `rfp-gates` and `rfp-assemble`. It surfaces only the flagged items — HIGH-confidence clean answers pass through auto-approved — so reviewer time is spent where it matters. Every correction written here becomes a future KB entry via `rfp-answer-bank.merge_corrections`. **This is where the learning loop closes**: without this skill logging structured corrections, the answer bank cannot improve, and the next RFP starts from the same baseline as this one.

### Cowork built-ins leveraged

- **Adaptive Cards** — drives the review queue card, per-item review cards, and before/after diff preview. The reviewer never leaves the card surface during a review session.
- **Excel** — appends event rows to the audit log on every queue build and every correction; also exports the corrections log as a portable xlsx for SME round-up and offline QA.
- **Enterprise Search** — invoked when a reviewer challenges a drafted response and wants to see the underlying source document, a prior RFP's answer to the same question, or the current KB entry with its citations.
- **Communications** — notifies the assigned reviewer when their queue is ready, nudges on the SLA, and sends the end-of-review thank-you summary with the learning-loop recap and merge CTA.

### Cross-links

- Reason semantics: `references/correction-taxonomy.md`
- When-does-an-item-enter-queue: `references/flagging-rules.md`
- Reviewer mental model and SLAs: `references/reviewer-workflow-guide.md`
- Reviewer one-pager (printable): `assets/correction-reason-catalog.md`
- Audit row schema: [audit-log-schema.md](../rfp-answer-bank/references/audit-log-schema.md)
- Audit append helper: [append_audit.py](../rfp-answer-bank/scripts/append_audit.py)

---
name: rfp-fit-assessment
description: |
  Step 2 of the RFP Agent Swarm workflow. Produces a Go/No-Go recommendation
  MEMO for a freshly intaked RFP by running a weighted qualification scorecard
  across seven dimensions (KB match, technical fit, commercial fit, competitive
  position, strategic alignment, resource availability, deadline feasibility)
  and surfacing evidence, risks, and kill-criteria. The human ALWAYS makes the
  final bid/no-bid call — this skill only produces data and analysis.

  Use when the user says things like:
    - "should we bid on this"
    - "go/no-go analysis"
    - "fit score this RFP"
    - "qualify this RFP"
    - "bid decision"
    - "assess this RFP"
    - "should we respond"
    - "run fit assessment"
    - "score this opportunity"
    - "is this RFP worth pursuing"
    - "qualify [buyer name] RFP"
    - "build the Go/No-Go memo for leadership"

  Do NOT use for: parsing raw RFP documents (use rfp-intake), drafting the
  actual answers (use rfp-respond), running quality gates on drafts
  (use rfp-gates), assembling the final response document (use rfp-assemble),
  or maintaining the reusable Q/A library (use rfp-answer-bank). Do NOT use
  this skill to AUTO-DECIDE — output is advisory; a named human owner signs.

  cowork:
    workflow: rfp-agent-swarm
    step: 2
    upstream: [rfp-intake, rfp-answer-bank]
    downstream: [rfp-respond]
    human_in_the_loop: true
---

# RFP Fit Assessment (Go / No-Go)

Step 2 in the RFP Agent Swarm. After `rfp-intake` has parsed the RFP into
structured metadata and a classified task list, this skill runs a transparent,
weighted qualification scorecard and assembles a one-page Go/No-Go memo so a
human owner can make an informed bid decision fast.

---

## When to Use

Invoke this skill when any of the following are true:

- A new RFP has just completed `rfp-intake` and a bid/no-bid decision is
  required before proposal work begins.
- An Account Executive (AE) or Proposal Lead asks for a "fit score",
  "qualification", or "should we bid" analysis on a specific opportunity.
- Leadership needs a standardised one-page memo to approve or decline pursuit.
- The answer-bank match rate needs to be estimated BEFORE committing SME hours.
- The team wants a reusable scorecard artefact to attach to CRM opportunity
  records for audit and retrospective analysis.

## When NOT to Use

| Situation | Use instead |
|---|---|
| Raw PDF / DOCX still needs parsing | `rfp-intake` |
| Drafts need answers generated | `rfp-respond` |
| Drafts need quality / compliance checks | `rfp-gates` |
| Human reviewer feedback to capture | `rfp-review` |
| Assembling the final submission doc | `rfp-assemble` |
| Maintaining reusable Q/A library | `rfp-answer-bank` |
| Autonomous bid/no-bid decision with no human | NOT SUPPORTED — this skill is advisory only |

---

## Quick Start (Worked Example)

Scenario: `rfp-intake` has just produced `working/rfp_metadata.json` and
`working/task_list.json` for "Acme HealthCo — Patient Portal Modernisation RFP,
deadline 2026-05-20, 142 questions".

```text
User: "Run fit assessment on the Acme HealthCo RFP"

Claude:
  1. Load working/rfp_metadata.json + working/task_list.json (from rfp-intake)
  2. Pull bank_stats.json from rfp-answer-bank (historical match rates)
  3. python scripts/kb_match_estimator.py
       --task-list working/task_list.json
       --bank-stats working/bank_stats.json
       --output working/kb_match_estimate.json
     => overall_estimate_pct: 68, confidence: MEDIUM
  4. Prompt human / AE for dimension scores 0-5 (technical, commercial,
     competitive, strategic, resource, deadline) — store in scorecard.json
  5. python scripts/compute_fit_score.py
       --scorecard working/scorecard.json
       --output working/fit_result.json
     => weighted total 71.5 -> band: CONDITIONAL
  6. python scripts/generate_go_no_go_memo.py
       --fit working/fit_result.json
       --kb working/kb_match_estimate.json
       --metadata working/rfp_metadata.json
       --template assets/go-no-go-memo-template.md
       --output working/go_no_go_memo.md
  7. Render Adaptive Card via render-ui (KPI row + risk donut + recommendation)
  8. (Optional) Hand working/go_no_go_memo.md to docx skill -> exec Word memo
  9. (Optional) Hand working/fit_result.json to xlsx skill -> detailed
     scorecard workbook with per-dimension evidence
```

Human decision owner (default: VP Sales) signs the memo. Only after sign-off
does `rfp-respond` begin.

---

## Core Instructions / Workflow

### Step-by-Step

1. **Ingest intake outputs.** Read `rfp_metadata.json` and `task_list.json`
   produced by `rfp-intake`. If missing, STOP and route the user back to
   `rfp-intake`.
2. **Estimate KB match rate.** Run `scripts/kb_match_estimator.py` against the
   task list and answer-bank historical stats. Record `overall_estimate_pct`
   and `confidence`.
3. **Gather dimension scores (0-5) from the AE / Proposal Lead.** Use the
   rubric in `references/fit-scoring-rubric.md`. KB-match dimension is
   pre-filled from step 2; the remaining six are human-supplied but rubric-
   anchored.
4. **Run the kill-criteria check.** See `references/fit-scoring-rubric.md`
   section "Kill Criteria". If ANY fire, flag on the memo — human still
   confirms.
5. **Compute weighted score.** Run `scripts/compute_fit_score.py`. Output
   band: Go (>=75), Conditional (50-74), No-Go (<50) — ADVISORY ONLY.
6. **Identify top risks & mitigations.** Pull from the dimension evidence
   fields; cross-reference `references/competitive-positioning-playbook.md`.
7. **Generate memo.** Run `scripts/generate_go_no_go_memo.py` with
   `assets/go-no-go-memo-template.md`.
8. **Render summary card** via `render-ui` (built-in) for quick review.
9. **Produce exec artefacts** (optional): one-page Word memo via `docx`;
   detailed workbook via `xlsx`.
10. **Route for human sign-off.** Named owner per
    `references/go-no-go-decision-criteria.md` RACI table.

### Scorecard Dimensions & Weights

| Dimension | Weight | Source | Rubric anchor |
|---|---|---|---|
| KB Match Rate (estimated) | 25% | `kb_match_estimator.py` + `rfp-answer-bank` | `references/fit-scoring-rubric.md` §1 |
| Technical Fit | 20% | Product / SE input | §2 |
| Commercial Fit | 15% | AE / Deal Desk | §3 |
| Competitive Positioning | 10% | AE + `competitive-positioning-playbook.md` | §4 |
| Strategic Alignment | 10% | Sales leadership | §5 |
| Resource Availability | 10% | Proposal Ops | §6 |
| Deadline Feasibility | 10% | Task list hours vs runway | §7 |
| **Total** | **100%** | — | — |

Weights MUST sum to 100; `compute_fit_score.py` enforces this.

### Recommendation Bands

| Score | Band | Default action | Human override? |
|---|---|---|---|
| >=75 | **Go** | Proceed to `rfp-respond` | Yes — strategic No-Go still allowed |
| 50-74 | **Conditional** | AE clarifies open questions, re-score | Yes — logo value can lift to Go |
| <50 | **No-Go** | Decline politely; log lessons | Yes — exec override requires written justification |

### Kill Criteria (Auto-Flag, Still Human-Confirmed)

See full table in `references/fit-scoring-rubric.md`. Examples:

- Mandatory certification we do not hold (e.g. FedRAMP High).
- Onsite / in-country data residency we cannot provide.
- Deal value below the commercial floor defined in Deal Desk policy.
- Exclusive incumbent relationship with a hard-locked renewal.

---

## Built-In Skills Used

| Cowork Skill | How this skill uses it |
|---|---|
| Adaptive Cards | Scorecard dashboard: KPI row (weighted_total, recommendation badge, confidence), radar/bar chart across 7 dimensions, FactSet of top strengths/risks, decision action buttons |
| Word | One-page Go/No-Go memo for exec sign-off (rendered from `working/go_no_go_memo.md`) |
| Excel | Detailed scoring workbook (per-dimension scores, weights, evidence, kill-criteria flags); also used to append rows to the shared `audit-log.xlsx` and to read KB exports for match estimation |
| Enterprise Search | Retrieve prior deal notes, competitor intel, past RFP outcomes with same buyer |
| Deep Research | Public buyer signals (press, filings, announcements, deep competitive analysis) to inform strategic alignment and competitive positioning scores |
| Email | Route finished memo + card to the named decision owner and AE |
| Calendar Management | Book the Go/No-Go decision meeting if score is in the Conditional band |
| Communications | Brief the AE / Proposal Lead in-channel with the recommendation summary |

No other built-ins are required. Do NOT invoke `PDF`, `PowerPoint`, `Meetings`,
`Scheduling`, `Daily Briefing`, or `M365 Search` for this step unless explicitly asked.

---

## Audit Log

This skill appends events to the shared RFP audit log at
`output/rfp-<rfp_id>/audit-log.xlsx`. Rows are appended via the **Excel**
built-in skill; the schema itself is owned by `rfp-answer-bank`.

| Event Type | When | Actor | Key fields |
|---|---|---|---|
| `FIT_ASSESSMENT_STARTED` | Skill invoked | AI | `rfp_id` |
| `SCORECARD_COMPUTED` | Scores computed across 7 dimensions | AI | `kb_match`, `tech_fit`, `commercial_fit`, `competitive`, `strategic`, `resource`, `deadline`, `weighted_total` |
| `GO_NO_GO_RECOMMENDED` | Recommendation generated | AI | `recommendation` (Go/No-Go), `rationale` |
| `HUMAN_DECISION_LOGGED` | Human makes final call | human | `decision` (Go/No-Go/Deferred), `decision_maker`, `decision_rationale` |

- Schema reference: [`audit-log-schema.md`](../rfp-answer-bank/references/audit-log-schema.md)
- Append helper (owned by `rfp-answer-bank`): [`append_audit.py`](../rfp-answer-bank/scripts/append_audit.py)
- Note: rows are appended via the **Excel** built-in; the schema and helper
  script are owned by `rfp-answer-bank` — do not fork or duplicate the schema
  here.

---

## Adaptive Card Dashboard

After `compute_fit_score.py` produces `working/fit_result.json`, this skill
renders a scorecard dashboard via the **Adaptive Cards** built-in. The card
is the primary human-facing review surface before sign-off.

Card layout:

- **KPI row** — `weighted_total` score, recommendation badge (Go / No-Go /
  Conditional), confidence label from the KB-match estimator.
- **Radar / bar chart** — all 7 dimensions plotted with their 0-5 scores:
  KB Match, Technical Fit, Commercial Fit, Competitive Positioning, Strategic
  Alignment, Resource Availability, Deadline Feasibility.
- **FactSet** — top 3 strengths (dimensions scoring >=4 with evidence) and
  top 3 risks (dimensions scoring <=2, or any kill-criterion flag).
- **Action buttons** —
  - `Approve — proceed to drafting` (unlocks `rfp-respond`)
  - `Decline`
  - `Defer for exec review`

After the human clicks an action button, this skill writes a
`HUMAN_DECISION_LOGGED` event to `output/rfp-<rfp_id>/audit-log.xlsx` with
the `decision`, `decision_maker`, and `decision_rationale` captured from the
card submission.

---

## Output Deliverables

| Output | Format | Producer | Consumer |
|---|---|---|---|
| `working/kb_match_estimate.json` | JSON | `scripts/kb_match_estimator.py` | memo generator; card |
| `working/fit_result.json` | JSON | `scripts/compute_fit_score.py` | memo generator; xlsx |
| `working/go_no_go_memo.md` | Markdown | `scripts/generate_go_no_go_memo.py` (+ `assets/go-no-go-memo-template.md`) | Word built-in; human |
| Adaptive Card | JSON payload | Adaptive Cards built-in | Human reviewer in chat |
| `working/go_no_go_memo.docx` | Word | Word built-in | Exec decision owner |
| `working/fit_scorecard.xlsx` | Excel | Excel built-in | Proposal Ops archive / CRM |
| `output/rfp-<rfp_id>/audit-log.xlsx` | Excel (append) | Excel built-in via `append_audit.py` | Shared audit trail (all RFP skills) |

---

## Guardrails

1. **The system does not decide. Ever.** Every output surfaces a named human
   decision owner. The score is a recommendation band, not an instruction.
2. **No freeform AI memo content.** `generate_go_no_go_memo.py` performs
   PURE template substitution on `assets/go-no-go-memo-template.md`. Do not
   rewrite, embellish, or omit placeholders.
3. **KB match is an ESTIMATE.** Always label it "estimated" on the memo and
   card. True match rate is only known after `rfp-respond` runs.
4. **Weights must sum to 100.** `compute_fit_score.py` validates and exits
   non-zero on mismatch. Do not silently normalise.
5. **Kill criteria are flags, not auto-declines.** Flag prominently on the
   memo; the human still signs.
6. **No external API calls from scripts.** Python 3 stdlib only. Any retrieval
   happens via built-in `Enterprise Search` / `Deep Research` in the agent
   loop, not inside scripts.
7. **Evidence required.** Any dimension score below 2 or above 4 MUST include
   an evidence string (1-2 sentences) referenced in the memo.
8. **Audit trail.** Persist `working/scorecard.json` and `fit_result.json`
   alongside the memo. The xlsx artefact is the archival record.

---

## Common Issues

| Symptom | Likely cause | Resolution |
|---|---|---|
| `compute_fit_score.py` exits with "weights do not sum to 100" | Manually edited weight in `scorecard.json` | Restore defaults from rubric table; re-run |
| KB match estimate flagged `confidence: LOW` | Fewer than 20 historical analogues in `bank_stats.json` | Proceed but mark estimate as provisional; re-check after `rfp-respond` |
| Memo has literal `[PLACEHOLDER]` tokens left | Missing field in `fit_result.json` or `rfp_metadata.json` | Re-run upstream step; do NOT hand-edit the memo |
| Score lands at 74 (just under Go) | Conditional band; score is sensitive to one dimension | Re-examine that dimension's evidence; do not round up |
| Kill criterion fires but AE wants to proceed | Strategic override by exec | Document written justification in memo `Risks & Mitigations`; require VP+ sign-off |
| Adaptive Card shows empty risk donut | No risks populated in `fit_result.json.risks[]` | Confirm dimensions <3 have evidence strings; risks auto-derive from those |
| Two reviewers produce very different scores on same dimension | Rubric anchor not applied | Use worked example in `references/fit-scoring-rubric.md` §"Calibration" |
| Deadline feasibility score inconsistent with task list hours | Task list stale | Re-run `rfp-intake` parse; recompute runway in hours |

---

## Related Skills

| Skill | Relationship |
|---|---|
| `rfp-intake` | **Upstream.** Produces `rfp_metadata.json` + `task_list.json` consumed here. |
| `rfp-answer-bank` | **Upstream substrate.** Provides historical match statistics used by `kb_match_estimator.py`; owns the audit-log schema. |
| `rfp-respond` | **Downstream.** Only runs AFTER a Go decision here. |
| `rfp-gates` | **Downstream of respond.** Quality/compliance gates on drafts. |
| `rfp-review` | **Downstream.** Captures human reviewer corrections. |
| `rfp-assemble` | **Downstream.** Builds the final submission document. |

### RFP chain

```
rfp-intake  ->  rfp-fit-assessment (THIS SKILL)  ->  rfp-respond  ->  rfp-gates  ->  rfp-review  ->  rfp-assemble
                              |
                              +-- rfp-answer-bank (substrate across all steps: KB, audit log, match stats)
```

- This skill **consumes** `rfp-intake`'s task list (`working/task_list.json`)
  and `rfp-answer-bank`'s KB match-rate estimate (`bank_stats.json` +
  `kb_match_estimator.py`).
- Its **approval unlocks `rfp-respond`** — no drafting begins until the
  human signs the Go/No-Go memo and `HUMAN_DECISION_LOGGED` is written with
  `decision = Go`.
- `rfp-answer-bank` is the shared substrate: it owns the knowledge base, the
  audit-log schema, and the `append_audit.py` helper consumed by every step
  in the chain.

### Cowork built-ins leveraged

| Built-in | How this skill leverages it |
|---|---|
| Excel | Append rows to `audit-log.xlsx`; read KB exports from `rfp-answer-bank` for match-rate estimation; emit detailed `fit_scorecard.xlsx` for archive/CRM |
| Adaptive Cards | Scorecard dashboard (KPI row, 7-dimension chart, strengths/risks FactSet, decision action buttons) |
| Enterprise Search | Competitive context, prior-deal notes, buyer history |
| Deep Research | Deep competitive analysis and public buyer signals feeding the strategic + competitive dimensions |
| Word | One-page Go/No-Go memo output for exec sign-off |
| Communications | Brief the AE / Proposal Lead in-channel with the recommendation summary |

---

## References

- [`references/fit-scoring-rubric.md`](references/fit-scoring-rubric.md)
  — dimension-by-dimension 0-5 anchors, weighting formula, worked example,
  kill criteria.
- [`references/go-no-go-decision-criteria.md`](references/go-no-go-decision-criteria.md)
  — decision matrix, stakeholder RACI, escalation timing, common patterns,
  AE question templates.
- [`references/competitive-positioning-playbook.md`](references/competitive-positioning-playbook.md)
  — incumbent/competitor inference, win-theme mapping, enrichment via
  Enterprise Search & Deep Research.

## Scripts

- [`scripts/compute_fit_score.py`](scripts/compute_fit_score.py)
  — weighted scorecard computation; emits band + per-dimension contributions.
- [`scripts/kb_match_estimator.py`](scripts/kb_match_estimator.py)
  — estimates % of questions answerable from the answer bank.
- [`scripts/generate_go_no_go_memo.py`](scripts/generate_go_no_go_memo.py)
  — deterministic template substitution to produce the Go/No-Go memo.

## Assets

- [`assets/go-no-go-memo-template.md`](assets/go-no-go-memo-template.md)
  — exec-brief one-page memo template with `[PLACEHOLDER]` tokens.

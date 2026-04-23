# Go / No-Go Decision Criteria

The weighted score produced by `scripts/compute_fit_score.py` is a
recommendation band. It is NEVER a decision. This document defines how the
band combines with strategic overrides, who owns the decision, and when to
escalate.

---

## Decision Matrix

Rows = score band. Columns = strategic override signal. Cells = default
action.

| Band \ Override | No override | Strategic logo / target vertical | Capacity constrained | Kill criterion fired |
|---|---|---|---|---|
| Go (>=75) | Proceed to `rfp-respond` | Proceed; assign top-tier SMEs | Proceed but de-prioritise lesser deals | Route to VP+ for written override |
| Conditional (50-74) | AE clarifies; re-score within 24h | Escalate to VP Sales; likely Go | Likely No-Go; capture lessons | Default No-Go; VP+ override required |
| No-Go (<50) | Decline politely; archive | Exec-only override with written justification | Decline | Decline |

A cell of "Proceed" never removes the requirement for the named human
decision owner to SIGN the memo.

---

## Stakeholder RACI

| Activity | AE | Proposal Lead | Product / SE | Deal Desk | Legal | VP Sales |
|---|---|---|---|---|---|---|
| Trigger fit assessment | A | R | C | I | I | I |
| Supply technical fit score | C | C | R / A | I | I | I |
| Supply commercial fit score | R | C | I | A | C | I |
| Supply competitive score | R / A | C | C | I | I | I |
| Supply strategic score | C | C | I | I | I | R / A |
| Supply resource score | I | R / A | C | I | I | I |
| Supply deadline score | I | R / A | I | I | I | I |
| Kill-criterion review | C | C | C | C | R | A |
| Sign the memo | C | C | I | I | C | **R / A** |

R = Responsible, A = Accountable, C = Consulted, I = Informed.

Default memo owner is VP Sales. For deals above a configured TCV threshold
(e.g. >$2M ARR) the signatory escalates one level per sales-policy.

---

## Timing Rules

| Situation | SLA |
|---|---|
| Standard Go/No-Go cycle from `rfp-intake` completion | 48 working hours |
| Conditional band -> AE clarification turnaround | 24 working hours |
| Kill criterion fired -> Legal + VP review | Same day |
| Re-score after material new info | Within 12 hours of info |
| Memo signed -> handoff to `rfp-respond` | Same day |

If the proposal deadline is within 5 working days of `rfp-intake`
completion, compress the cycle: AE clarification becomes 4 hours, exec
review same-day, with the Proposal Lead as temporary A-owner if VP Sales
is unreachable.

---

## Common Patterns

### Pattern A — High KB match, low commercial fit

Symptom: KB match 4-5, Commercial 1-2, overall lands Conditional.

Interpretation: We CAN answer it, but we cannot profitably WIN it as
written. Typical action: AE negotiates scope/price/terms with the buyer
BEFORE we commit response effort. Re-score once revised commercials are
in hand. If no movement from buyer, default to No-Go.

### Pattern B — Low KB match, strategic logo

Symptom: KB match 1-2, Strategic 5, overall lands Conditional or No-Go.

Interpretation: High SME cost but marquee logo value. Requires a VP Sales
override WITH named SME commitments. Memo must quantify SME hours
(typically 3-5x a standard response) and route through Proposal Ops
capacity tracker.

### Pattern C — Short deadline, high-value customer

Symptom: Deadline 0-1, every other dimension 4-5, overall lands Go.

Interpretation: We want it, but physics may not cooperate. Proposal Lead
MUST produce a written response plan (hours/day breakdown, SME blocks
booked) as an attachment to the memo before sign-off.

### Pattern D — All-green except competitive

Symptom: Competitive 0-1, others 4-5. Overall just above 75.

Interpretation: Likely column fodder for an incumbent. Check
`competitive-positioning-playbook.md` for tell-tale signs. If confirmed,
default to No-Go regardless of score — AE must justify pursuit.

### Pattern E — Kill criterion fires but score is high

Symptom: e.g. score 82, but missing FedRAMP High.

Interpretation: Score is misleading. Kill criterion dominates. Default
No-Go; route to Legal and VP for written override only.

### Pattern F — Resource availability is the sole blocker

Symptom: Resource 1, everything else >=4. Overall 70-74.

Interpretation: Proposal Ops must confirm if reprioritising two other
open RFPs frees the SMEs. Do NOT commit without that confirmation.

---

## AE Clarification Questions (Conditional Band)

Use this checklist verbatim when the memo is Conditional. Capture
answers in `working/ae_qanda.json` for audit.

1. What is the true deal size (TCV and ARR) and the buyer's budget band?
2. Is there a named incumbent? If yes, what is their renewal timing?
3. Which competitors are confirmed shortlisted?
4. Is the RFP text negotiable (can scope/terms be revised)?
5. Which buyer stakeholder is the economic buyer? Have we met them?
6. Has the buyer seen a demo? Do they have a preferred vendor?
7. What is the reference-ability expectation (logo use, case study)?
8. Are there hard commercial floors (e.g. discount caps) we must meet?
9. Is the deadline fixed or a "preferred-by"?
10. What is the follow-on expansion opportunity after this win?

---

## Sign-Off Rules

- Memo must have a named signatory (default VP Sales).
- A Conditional memo requires TWO signatures: Proposal Lead + VP Sales.
- A No-Go memo requires ONE signatory: VP Sales, with lessons-learned
  paragraph captured for `rfp-answer-bank` archival.
- Every signature is a dated entry; silent approval is not permitted.
- Kill-criterion override requires an additional Legal sign-off on the
  memo.

---

## Handoff to `rfp-respond`

Upon a signed Go (or overridden Conditional):

1. `working/go_no_go_memo.md`, `.docx`, and `fit_scorecard.xlsx` archive
   to the opportunity record.
2. `working/kb_match_estimate.json` passes to `rfp-respond` as the
   starting match-rate hypothesis.
3. `working/scorecard.json` retained for post-win/post-loss retrospective.

No `rfp-respond` work begins before the memo is signed and archived.

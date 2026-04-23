# Go / No-Go Memo — [RFP_TITLE]

**Buyer:** [BUYER_NAME]
**Submission deadline:** [DEADLINE]
**Generated (UTC):** [GENERATED_AT]
**Decision owner (sign below):** [DECISION_OWNER]

---

## 1. Summary

This memo presents a scored qualification for the above RFP. The scorecard
is ADVISORY. A named human decision owner signs below.

- Overall weighted score: **[OVERALL_SCORE] / 100**
- Recommendation band: **[RECOMMENDATION]**
- Estimated answer-bank match rate: **[KB_MATCH_PCT]** (confidence: [KB_CONFIDENCE])
- Estimated SME hours to respond: **[SME_HOURS_ESTIMATE]**

> The system does not decide. This memo surfaces evidence so a human can.

---

## 2. Recommendation

**[RECOMMENDATION]**

Record the final decision in the Sign-Off block at the bottom of this memo.
Any override of the recommendation band must include a written justification
paragraph in the Sign-Off block.

---

## 3. Scorecard Snapshot

| Dimension | Weight | Score |
|---|---|---|
| KB Match Rate (estimated) | 25% | [KB_MATCH_PCT] (confidence [KB_CONFIDENCE]) |
| Technical Fit | 20% | [TECHNICAL_FIT] |
| Commercial Fit | 15% | [COMMERCIAL_FIT] |
| Competitive Positioning | 10% | [COMPETITIVE_FIT] |
| Strategic Alignment | 10% | [STRATEGIC_FIT] |
| Resource Availability | 10% | [RESOURCE_FIT] |
| Deadline Feasibility | 10% | [DEADLINE_FIT] |
| **Weighted total** | **100%** | **[OVERALL_SCORE] / 100** |

Full per-dimension breakdown with evidence is attached as the detailed
scorecard workbook (`fit_scorecard.xlsx`, produced by the `xlsx` built-in).

---

## 4. Key Evidence

- KB match is an ESTIMATE. True rate will be known only after `rfp-respond`
  executes against the live answer bank.
- Dimension scores follow the anchored rubric in
  `references/fit-scoring-rubric.md`.
- Competitive positioning uses signals documented in
  `references/competitive-positioning-playbook.md`.
- Resource and deadline feasibility pull from the task list produced by
  `rfp-intake` and Proposal Ops capacity records.

---

## 5. Risks & Mitigations

**Top risks (auto-derived from dimensions scored <=2):**

[TOP_RISKS_BULLETS]

**Proposed mitigations (AE / Proposal Lead to confirm before sign-off):**

[MITIGATIONS_BULLETS]

**Kill criteria flagged:**

[KILL_CRITERIA_BULLETS]

If any kill criterion is flagged, Legal review and VP+ written override
are required before a GO decision is valid.

---

## 6. Resource Impact

- Estimated SME hours: [SME_HOURS_ESTIMATE]
- Proposal team window: see Proposal Ops capacity tracker
- Expected answer-bank coverage: [KB_MATCH_PCT] — remainder requires SME
  authoring and review
- Quality gates ([`rfp-gates`](../rfp-gates/SKILL.md)) will run on all
  drafts before human review
- Human review ([`rfp-review`](../rfp-review/SKILL.md)) will capture any
  corrections back into the answer bank

---

## 7. Decision Required — Sign-Off Block

Delete the rows that do not apply; retain and complete the one that does.

**GO (advisory score [OVERALL_SCORE]):**

- Signed: ____________________________  ([DECISION_OWNER])
- Date: ____________________
- Comments / scope guardrails: ____________________________________________

**CONDITIONAL — proceed after AE clarifications:**

- Open questions routed to AE (list): _____________________________________
- Re-score owner: ________________________  Due: ____________________
- Signed (Proposal Lead): ____________________________
- Signed (VP Sales): __________________________________

**NO-GO:**

- Signed: ____________________________  ([DECISION_OWNER])
- Date: ____________________
- Lessons-learned (captured to `rfp-answer-bank`): ________________________

**OVERRIDE (recommendation band not followed):**

- Override direction (circle): GO -> NO-GO   /   NO-GO -> GO
- Written justification (mandatory): _______________________________________
- Signed (VP Sales or above): _____________________________________________
- Legal acknowledgement (required if kill criterion flagged): _____________

---

## 8. Handoff

On a signed GO:

1. This memo is archived as `working/go_no_go_memo.md` and exported to
   `working/go_no_go_memo.docx` via the `docx` built-in.
2. `working/fit_scorecard.xlsx` archives to the CRM opportunity record.
3. `rfp-respond` begins (next step in the workflow).

On a signed NO-GO:

1. Decline notification drafted (use `Email` built-in).
2. Lessons-learned captured in `rfp-answer-bank`.
3. Opportunity marked Closed - No Bid in CRM.

_End of memo._

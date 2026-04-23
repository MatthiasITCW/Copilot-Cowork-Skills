# Correction Reason Catalog — Reviewer One-Pager

Organisation: **[ORG_NAME]** &nbsp;&nbsp;|&nbsp;&nbsp; Knowledge base: **[KB_SYSTEM_NAME]** (Loopio in POC)

Pick the **most specific** reason. When two could apply, pick the one with the stronger KB action. Every correction you log here feeds the learning loop — the next RFP uses the updated bank.

| Reason | One-line definition | Concrete example | What happens next |
|--------|---------------------|------------------|-------------------|
| **FACTUAL_ERROR** | Answer contained a wrong fact. | Drafter said "PII retained 90 days." Actual policy: 30. | `[KB_SYSTEM_NAME]` entry is **replaced** with your corrected answer. All future drafters use the new fact. |
| **OUTDATED_SOURCE** | KB entry used to be right, now stale. | "SOC 2 audit Q3 2024" is now Q1 2026. | KB entry is **replaced** and freshness date reset. Watch for a spike — signals a freshness sweep is overdue. |
| **TONE_OR_STYLE** | Reworded, no fact change. | "Our system utilizes encryption" → "We encrypt all data at rest." | **No-op** against the KB. Logged for metrics only. If these spike, the drafter's voice model will be retuned. |
| **MISSING_CONTEXT** | Correct answer, lacked buyer-specific detail. | Added Okta OIN listing number to a generic SSO answer. | **Sibling entry** is added to the KB. Drafters will pick the matching sibling for similar buyers next time. |
| **CATEGORY_MISCLASSIFICATION** | Question went to the wrong team. | Security question landed with Product. | **Routing map** updated. Does not change the answer itself; combine with another reason if the answer was also wrong. |
| **UNANSWERABLE_FROM_KB** | No KB entry existed; SME provided one. | First time anyone asked about EU AI Act Article 6. | **New entry** created from the SME answer. Question pattern indexed so similar phrasings match next time. |
| **POLICY_UPDATE** | Company position has actually changed. | "No on-prem" → "On-prem for Enterprise from Q2 2026." | Old entry **retired**, new entry added. In-flight RFPs using the old entry are flagged for re-review. Requires Legal/Exec sign-off. |
| **COMPLIANCE_NUANCE** | Jurisdiction-specific tweak needed. | Quebec Law 25 additions to a GDPR answer. | **Sibling entry** scoped by jurisdiction. Legal tracks expiry on regulatory cycles. |

---

## Quick decision chips

- **Factual vs tone?** If you changed a number, a date, a product name, or a capability, it is **not** tone.
- **Factual vs policy?** Was the KB ever right for anyone? If yes → `FACTUAL_ERROR`. If the company is changing position → `POLICY_UPDATE`.
- **Missing context vs compliance nuance?** Is the context commercial (buyer, industry, integration)? `MISSING_CONTEXT`. Is it regulatory (jurisdiction, law)? `COMPLIANCE_NUANCE`.
- **Unanswerable vs factual error?** Did any KB entry match the question? If no → `UNANSWERABLE_FROM_KB` and pull in an SME. If yes but it was wrong → `FACTUAL_ERROR`.

---

## What you do not do

- You do **not** edit `[KB_SYSTEM_NAME]` directly. The learning loop handles that at the next bank refresh.
- You do **not** need to provide a KB action. The reason you pick determines the action.
- You do **not** need to reconcile conflicts with prior entries. `merge_corrections` handles supersession.

---

## Escalation signals

- `POLICY_UPDATE`: loop in **Legal** and the relevant domain **Exec Sponsor** before committing.
- `UNANSWERABLE_FROM_KB`: attach an **SME email** in the correction; the script will block the commit without one.
- If you are editing a Security / Legal / Pricing / Compliance answer, a confirmation checkbox appears — this is intentional friction.

---

## Auto-behaviour to be aware of

- If you pick `TONE_OR_STYLE` but your edit changes more than ~120 characters, the script will auto-reclassify to `FACTUAL_ERROR` and ask you to confirm. This catches silent factual edits dressed as "tone."
- Duplicate submissions (same question id, same reviewer, same corrected text) are silently ignored — safe to re-run.
- Every response in the final assembled package carries a `review_status` (`reviewed`, `auto-approved`, or `skipped`). If you see an item without one, flag it: the pipeline treats that as a defect.

---

## Timing and SLAs

| Reason | Typical review time | Who signs off |
|--------|---------------------|----------------|
| FACTUAL_ERROR | 2-5 minutes | Reviewer alone |
| OUTDATED_SOURCE | 1-3 minutes | Reviewer alone |
| TONE_OR_STYLE | < 1 minute | Reviewer alone |
| MISSING_CONTEXT | 3-7 minutes | Reviewer; optional Account Exec ping |
| CATEGORY_MISCLASSIFICATION | 1 minute | Reviewer alone |
| UNANSWERABLE_FROM_KB | 15-45 minutes | SME writes, reviewer logs |
| POLICY_UPDATE | 20-60 minutes + day-scale sign-off | Legal + Exec Sponsor |
| COMPLIANCE_NUANCE | 5-15 minutes | Reviewer; Legal on first occurrence |

---

## Worked examples — what to pick

**Example 1.** The drafter wrote "We comply with GDPR and the forthcoming EU AI Act." The EU AI Act has in fact been enacted. Fix: replace "forthcoming" with "enacted." Reason: **FACTUAL_ERROR** (not tone — the word "forthcoming" carried information).

**Example 2.** The drafter wrote "Our encryption is best-in-class." You rewrote to "All data at rest is encrypted with AES-256; keys are rotated quarterly." Reason: **MISSING_CONTEXT** — the original sentence did not lie, but it was missing the specific facts the buyer needs.

**Example 3.** The drafter wrote a correct SOC 2 answer, but it went to the Legal reviewer rather than Security. You route it to Security and the answer is fine. Reason: **CATEGORY_MISCLASSIFICATION** (no content change needed).

**Example 4.** The drafter had no answer at all for a question about Quebec Law 25. You ask Legal, Legal provides an answer. Reason: **UNANSWERABLE_FROM_KB** with a `COMPLIANCE_NUANCE` secondary tag — the first reason drives the KB action (add-new), the tag helps future clustering.

---

*Placeholder note: replace `[ORG_NAME]` and `[KB_SYSTEM_NAME]` before printing for your org. Review this catalog quarterly with the RFP ops owner. Print double-sided; the front page (triggers table) is the one reviewers keep on their desk.*

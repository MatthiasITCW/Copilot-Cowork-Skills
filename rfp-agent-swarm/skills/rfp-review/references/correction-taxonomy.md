# Correction Taxonomy

The taxonomy is the vocabulary the learning loop uses to decide what to do with a correction. `log_correction.py` rejects any reason not in this list. The set is deliberately small (8 reasons) — if you find yourself wanting a ninth, first check whether an existing one fits.

Rule of thumb for reviewers: **pick the most specific reason**. If both `TONE_OR_STYLE` and `FACTUAL_ERROR` could apply, it is `FACTUAL_ERROR`.

## 1. FACTUAL_ERROR

**Definition.** The drafted answer contained a wrong fact. The gold answer is now known and documented in the correction.

**Example.** Drafted answer said "PII retained for 90 days." True policy is 30 days. Reviewer rewrites to "30 days" and selects `FACTUAL_ERROR`.

**KB action on merge.** `replace`. The existing KB entry is overwritten with the corrected answer. Old version is kept in the KB history log, not shown to drafters.

**Reviewer guidance.** Use this when the fact was wrong *and* you are confident the corrected fact is right for future RFPs, not just this one. If the corrected fact is buyer-specific, use `MISSING_CONTEXT` instead.

## 2. OUTDATED_SOURCE

**Definition.** The KB entry used to be correct but has become stale. A newer version now exists.

**Example.** KB says "SOC 2 Type II, audit Q3 2024." Current audit is Q1 2026. Reviewer updates the date and selects `OUTDATED_SOURCE`.

**KB action on merge.** `replace` with a version bump. Freshness timestamp is reset.

**Reviewer guidance.** Use this when the answer was right historically but drifted. Distinguishes "we were wrong" (FACTUAL_ERROR) from "we changed" over time (OUTDATED_SOURCE). Both merge as replace, but the distinction matters for reporting: if OUTDATED_SOURCE corrections spike, the answer bank needs a freshness sweep, not a factual audit.

## 3. TONE_OR_STYLE

**Definition.** No fact changed. You reworded for clarity, voice, or buyer tone.

**Example.** Drafted answer: "We do encryption." Reviewer: "All data at rest is encrypted with AES-256; keys are rotated quarterly." Same fact, better phrasing. Actually — that is `MISSING_CONTEXT`. A true `TONE_OR_STYLE`: drafted "Our system utilizes encryption" → reviewer "We encrypt all data at rest." Same information, shorter.

**KB action on merge.** `no-op` (logged for metrics but does not touch the KB).

**Reviewer guidance.** Low learning value. Still logged, because a spike in `TONE_OR_STYLE` signals the drafter's voice model is drifting and needs retuning. If your edit added any information the drafter did not have, it is not tone — it is `MISSING_CONTEXT` at minimum.

## 4. MISSING_CONTEXT

**Definition.** The answer was correct, but it lacked buyer-specific context that made it more persuasive or complete for this RFP.

**Example.** Standard answer: "Yes, we support SSO via SAML 2.0." For a buyer that asked specifically about Okta, reviewer adds: "Yes, we support SSO via SAML 2.0 with a certified Okta integration (OIN listing #1234)." Same core fact, Okta-specific context added.

**KB action on merge.** `add-sibling`. Creates a buyer-specific or context-specific variant of the KB entry; the original is kept. The drafter can now pick the best match based on buyer metadata.

**Reviewer guidance.** Use this when the core fact was right but you added detail that should be available for similar buyers next time. Do NOT use this when the added detail is so specific it will never repeat (e.g., a one-off security clause) — in that case just approve with a tone edit.

## 5. CATEGORY_MISCLASSIFICATION

**Definition.** The question was routed to the wrong team / reviewer. The answer may or may not have been correct, but the underlying problem is routing.

**Example.** A question about SOC 2 scope was routed to Product instead of Security. Reviewer flags this reason and reassigns.

**KB action on merge.** `reclassify`. Updates the category mapping used by the drafter so future questions with this pattern go to the right team.

**Reviewer guidance.** Combine with another reason if the answer was also wrong. The primary reason is still the content correction; record the misclassification as a secondary tag (the log format supports `reasons: [...]` array but only the first drives KB action).

## 6. UNANSWERABLE_FROM_KB

**Definition.** The drafter could not answer because no KB entry exists. An SME has now provided one.

**Example.** New question: "Do you comply with the EU AI Act Article 6 high-risk classification?" Nothing in the KB. SME drafts an answer; reviewer logs it.

**KB action on merge.** `add-new`. Creates a new KB entry with the SME answer. Question pattern is indexed so similar phrasings match next time.

**Reviewer guidance.** The SME, not the reviewer, should be the one phrasing the answer. The reviewer's job is to capture it verbatim and tag the category so routing works next time.

## 7. POLICY_UPDATE

**Definition.** The company's position has changed. The old KB entry is no longer correct for anyone.

**Example.** Old position: "We do not support on-premises deployment." New position: "We support on-prem for enterprise tier only, starting Q2 2026." Reviewer selects `POLICY_UPDATE` and provides the new answer.

**KB action on merge.** `retire + add-new`. The old entry is retired (not deleted — retained for historical queries) and the new answer is added. Any RFPs in flight that used the old entry are flagged for re-review.

**Reviewer guidance.** This is the highest-impact reason. Use sparingly and always loop in Legal or Exec. If you are not sure whether this is a policy update or a one-off exception, treat it as a `FACTUAL_ERROR` first — you can always upgrade to `POLICY_UPDATE` later.

## 8. COMPLIANCE_NUANCE

**Definition.** The standard answer was correct, but needed a jurisdiction- or regulation-specific adjustment for this buyer.

**Example.** Standard answer: "We comply with GDPR." For a buyer in Quebec, reviewer adds Law 25 specifics. The standard answer is still correct for most buyers; the Quebec answer is a sibling.

**KB action on merge.** `add-sibling`, scoped by jurisdiction tag. The drafter will pick the jurisdiction-appropriate sibling when buyer metadata indicates it.

**Reviewer guidance.** Very similar to `MISSING_CONTEXT` — the difference is the context here is regulatory, not commercial. This distinction matters because compliance siblings expire on regulatory change cycles (usually tracked by Legal), whereas `MISSING_CONTEXT` siblings expire when the buyer relationship changes.

## Mapping summary

| Reason                     | KB action          | Impact radius               | Typical follow-up                   |
|----------------------------|--------------------|-----------------------------|-------------------------------------|
| FACTUAL_ERROR              | replace            | All future RFPs             | None                                |
| OUTDATED_SOURCE            | replace + freshness| All future RFPs             | Freshness sweep if frequent         |
| TONE_OR_STYLE              | no-op              | Metrics only                | Retune drafter if frequent          |
| MISSING_CONTEXT            | add-sibling        | Buyers matching context     | None                                |
| CATEGORY_MISCLASSIFICATION | reclassify         | Routing for similar Qs      | None                                |
| UNANSWERABLE_FROM_KB       | add-new            | All future RFPs             | Index the question pattern          |
| POLICY_UPDATE              | retire + add-new   | All future RFPs + in-flight | Legal/Exec sign-off, re-review flag |
| COMPLIANCE_NUANCE          | add-sibling        | Jurisdiction match          | Legal tracks expiry                 |

## What happens if the reason is ambiguous

`log_correction.py` supports a `reasons: [...]` array in the JSONL record, but only the **first** entry drives the KB action. Secondary entries are tags, not decisions. This is deliberate: if the taxonomy feels ambiguous, the reviewer is forced to rank, not hedge.

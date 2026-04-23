# Retrieval-First Playbook

This playbook governs how `rfp-respond` turns a single RFP question into a draft answer. It is the operational companion to `SKILL.md` section 5.

The single rule that overrides everything else: **we retrieve before we generate, and when we generate we say so.**

## 1. Retrieval Flow

```
  +----------------------+
  |   RFP question Qn    |
  +----------+-----------+
             |
             v
  +----------------------+
  | query formulation    |   (see §2)
  |   - acronym expand   |
  |   - synonym add      |
  |   - paraphrase       |
  +----------+-----------+
             |
             v
  +-------------------------------------+
  | rfp-answer-bank/scripts/search_bank |
  |  hybrid: keyword + vector +         |
  |  semantic reranker                  |
  +----------+--------------------------+
             |
             v
  +----------------------+
  | top-k candidates     |
  +----------+-----------+
             |
             v
  +-------------------------------------+
  | confidence_scorer.py                |
  |  reranker score -> tier             |
  +----------+--------------------------+
             |
       +-----+------+------------+
       |            |            |
       v            v            v
     HIGH         MEDIUM         LOW
   verbatim      adapt         generate
                record         + caveat
                delta          + flag
                              cap at 75
```

## 2. Query Formulation Rules

A well-formed query materially improves reranker score. `draft_responses.py` constructs three query variants and keeps the highest-scoring:

1. **Verbatim**: the question text as written, whitespace-normalised.
2. **Expanded**: acronyms unfolded from a maintained glossary (`SSO` → `Single Sign-On SSO`; `MFA` → `Multi-Factor Authentication MFA`). Keep the acronym in the query — many bank entries index it.
3. **Paraphrased**: a simple restatement using canonical terms from our product vocabulary (e.g. "tenancy isolation" → "logical tenant isolation").

Never rewrite the question to make a match more likely. Paraphrasing is to bridge vocabulary, not to change meaning.

### Re-query triggers

Re-query once, and only once, when:

- Top reranker score < 0.50 (likely vocabulary mismatch)
- Top candidate was last approved > 18 months ago AND score is 0.75–0.85 (try for a fresher match)
- The question explicitly names a control framework (SOC 2, ISO 27001, GDPR) and no candidate references it

If re-query does not improve the tier, escalate to LOW. Do not loop.

## 3. HIGH: Verbatim Reuse

Trigger: reranker score ≥ 0.90 and category tag matches.

Rules:

- Copy `response_text` exactly as approved in the bank.
- Do not shorten, "polish", or reformat.
- If the buyer asks for a word limit shorter than the bank entry, flag as MEDIUM instead — a trim is an adaptation.
- Preserve all footnote markers, links, and defined terms.

Provenance recorded: `bank_entry_id`, `last_approved_date`, `original_question`.

Example:

> Buyer question: "Do you support SAML 2.0 SSO?"
> Bank entry BANK-0412 (approved 2026-01-20, score 0.94):
> "Yes. [Product] supports SAML 2.0 SSO with IdP-initiated and SP-initiated flows. Tested with Okta, Azure AD, Ping, and Google Workspace."
> Drafted answer: verbatim copy. Tier HIGH, confidence 94.

## 4. MEDIUM: Adapt From a Related Entry

Trigger: reranker score 0.75–0.89.

### Allowed edits

| Edit | Example |
|---|---|
| Tighten | Remove a paragraph irrelevant to the buyer's question |
| Specialise to buyer context | Replace "our customers" with "organisations in [buyer sector]" where accurate |
| Trim to word limit | Drop a supporting sentence; keep the claim |
| Reorder | Put the direct yes/no first |
| Stitch two adjacent bank entries | If both score MEDIUM and are complementary (e.g. encryption-at-rest + encryption-in-transit) |

### Disallowed edits

| Edit | Why |
|---|---|
| Add a new claim | Claims must trace to an approved source |
| Inflate capability ("basic" → "best-in-class") | Marketing fluff and misrepresentation risk |
| Change defined terms | "Customer Data" has a contractual meaning |
| Add a certification or audit date not in the source | Fabrication risk |
| Extend scope (e.g. "US-only" → "global") | Factual drift |

Every MEDIUM answer must record a `delta_summary` describing what changed, in ≤ 160 characters. Example: `"tightened to 50-word limit; scoped to EU data residency only"`.

### Worked MEDIUM example

> Buyer question: "Describe your approach to encryption in transit for customer data in the EU."
> Bank entry BANK-0221 (score 0.83): a 180-word description of global encryption-in-transit posture.
> Adapted answer: first 60 words retained; replaced "globally" with "within the EU region (eu-west-1, eu-central-1)"; added sentence referencing DPA §7.2 (already present in approved annex).
> `delta_summary`: "scoped to EU regions; cross-referenced DPA §7.2"
> Tier MEDIUM, confidence 83.

## 5. LOW: Generate With Caveats

Trigger: reranker score < 0.75 or no candidate passes category check.

Rules:

1. Attach the preamble from `assets/response-preamble-template.md`.
2. Confidence is **capped at 75**, regardless of how good the generated text looks.
3. `flags` must include `REVIEWER_REQUIRED`. `reviewer_required = true`.
4. If the question touches pricing, certifications, audit timelines, or customer references, do not generate — emit `NEEDS_AUTHORISED_INPUT` instead.
5. The generated text must explicitly acknowledge uncertainty where relevant: "Subject to SME confirmation", "Based on current published roadmap", etc.
6. Never invent a number, date, or proper noun.

### Worked LOW example

> Buyer question: "Describe how your product detects anomalous SCIM provisioning events triggered by a compromised IdP token."
> Bank top-match score 0.61 (general SCIM support, not anomaly detection).
> Generated draft, with preamble:
>
> *"The following response was generated based on [general SCIM documentation BANK-0118]. It has been flagged for SME review before submission. Confidence tier: LOW. Reviewer: [Security Lead]."*
>
> "[Product] logs all SCIM provisioning events and forwards them to the tenant's configured SIEM. Detection of anomalous patterns (e.g. bulk deprovisioning, privilege escalation) is subject to SME confirmation and not currently documented as a productised feature."
>
> Tier LOW, confidence 68. Flag: REVIEWER_REQUIRED, SME: Security Lead.

## 6. Stitching and Multi-Part Questions

Some RFP questions are compound ("Describe your SSO support **and** how it integrates with MFA"). Rules:

- Search each sub-question independently.
- Each sub-answer gets its own tier.
- The composite answer's tier is the **lowest** of its parts.
- Composite `delta_summary` lists the stitched `bank_entry_id`s.

## 7. When to Escalate Instead of Retry

Escalate (do not re-query) when:

- The question is genuinely novel for the product (new market, new feature not yet shipped).
- The question asks for a forward-looking commitment (roadmap dates, custom SLAs).
- The question requires a customer-specific commercial negotiation.

Escalation path: emit `NEEDS_SME` flag, assign to the relevant team lead, and let `rfp-review` handle routing. This skill never blocks — it flags and continues.

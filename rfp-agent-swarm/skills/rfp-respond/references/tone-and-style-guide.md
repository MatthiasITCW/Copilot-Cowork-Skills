# Tone and Style Guide

How RFP responses drafted by `rfp-respond` should read. This guide is enforced partly by `scripts/draft_responses.py` (banned-phrase detection) and partly by `rfp-gates` (voice and concision checks).

## 1. Voice

Confident, factual, concrete. Buyers are evaluating us; they are reading many responses; they want evidence, not enthusiasm.

| Do | Don't |
|---|---|
| State the capability directly, then support it | Lead with "We are thrilled to…" |
| Name the component, version, SLA number, region | Use vague collective terms ("our platform", "our stack") |
| Let the facts do the work | Add intensifiers ("extremely robust", "highly secure") |
| Acknowledge limits honestly where the bank says to | Paper over gaps with superlatives |

### Before / after

> Before: "Our world-class, industry-leading security platform provides unparalleled protection for your most critical data assets, leveraging best-in-class encryption to deliver peace of mind."
>
> After: "Customer data is encrypted at rest with AES-256 and in transit with TLS 1.2+. Keys are managed in AWS KMS with per-tenant CMK isolation. See annex §4.2 for the detailed key-lifecycle diagram."

## 2. Concision Targets

| Response type | Target length | Hard ceiling |
|---|---|---|
| Short-answer (yes/no, single fact) | 1–2 sentences | 40 words |
| Medium (capability description) | 3–6 sentences | 120 words |
| Long-narrative (architecture, approach) | 2–4 paragraphs | 350 words |

If the buyer specifies a word or character limit, it takes precedence over these targets. Exceeding a buyer-specified limit is a hard fail in `rfp-gates`.

## 3. Structural Pattern

Allowed structural patterns for a well-formed answer:

1. **Summary sentence** — answers the question directly.
2. **Supporting facts** — 1–4 concrete, sourced details.
3. **Reference** — pointer to annex, policy, SLA, DPA, or case study where the buyer can verify.

Example:

> "[Product] supports SAML 2.0 and OIDC SSO." *(summary)*
> "Integration is tested quarterly with Okta, Azure AD, Ping, and Google Workspace. Group mapping is supported via SCIM 2.0. MFA step-up is enforced by policy in the IdP." *(supporting facts)*
> "Configuration guide: annex §3.1." *(reference)*

## 4. Active Voice and Specificity

Prefer active voice with a named actor. "The system encrypts data" beats "Data is encrypted". Better still: "[Product]'s storage layer encrypts data with AES-256 before writing to S3".

Specifics that must appear where applicable:

| Question touches… | Include |
|---|---|
| Encryption | Algorithm (AES-256, TLS 1.2+), key management system, key rotation cadence |
| SLA | Exact percentage, measurement window, exclusions pointer |
| Deployment | Cloud provider(s), region(s), tenancy model |
| Integrations | Named IdPs/systems tested, API version, rate limits |
| Compliance | Framework, report year, auditor (if public), scope |
| References | Industry, size, region, use-case |

## 5. Banned Phrases

`scripts/draft_responses.py` scans drafts and rejects or flags these. The full list is maintained in the script's `BANNED_PHRASES` constant.

| Phrase | Why banned |
|---|---|
| "world-class" | Meaningless superlative |
| "industry-leading" | Unverifiable claim |
| "best-in-class" | Unverifiable claim |
| "cutting-edge" | Vague; dates badly |
| "state-of-the-art" | Vague; dates badly |
| "robust" (as lone adjective) | Empty intensifier |
| "seamless" | Sales cliché; rarely true |
| "peace of mind" | Emotional appeal, not evidence |
| "turnkey" | Overpromises effort |
| "military-grade encryption" | Meaningless; AES-256 is AES-256 |
| "bank-grade security" | Meaningless |
| "leverage" (as verb) | Use "use" |
| "synergy" | Buzzword |
| "unparalleled" | Unverifiable |
| "holistic" | Vague |

## 6. Numbers and Dates

- Always cite the source of a number (bank entry ID) in the response metadata, even if the number itself is inlined.
- Dates in ISO 8601 format inside metadata; human-readable form in the prose ("February 2026").
- Never round up. If the figure is 99.92%, write 99.92%, not 99.9% or 99.95%.
- Never reuse a figure across unrelated claims. A single approved number belongs to a single claim.

## 7. Defined Terms

Defined terms from our MSA, DPA, SLA, and AUP are capitalised and must not be paraphrased inside responses (e.g. "Customer Data", "Authorised Users", "Service", "Support Hours"). Replacing a defined term with a synonym is a contract risk and is rejected by `rfp-gates`.

## 8. Formatting

| Element | Rule |
|---|---|
| Bullets | Use only when the bank entry uses them or the answer is a genuine list (≥ 3 items) |
| Bold | For yes/no answers and control-framework names; not for emphasis |
| Tables | Preserve from bank entries; do not invent |
| Links | Use reference-style to the annex section; do not insert raw URLs to marketing pages |
| Headings | Only within long-narrative responses (> 200 words); use H3 at most |

## 9. Tone by Team

| Team | Slant |
|---|---|
| Security | Precise, factual, framework-aware. Slightly terser than average. |
| Technical | Specific, versioned, concrete. Quote the limits honestly. |
| Commercial | Warmer in company/case-study sections; factual in pricing; legalistic in redline responses. |

Differences are stylistic; all three teams share the banned-phrase list and the structural pattern.

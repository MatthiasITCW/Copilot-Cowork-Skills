# KB Entry Template (SME Submission)

Use this template verbatim when an Contoso SME submits a new answer for the bank.
Replace every [BRACKETED] placeholder. Leave no placeholders in the final version.

---

**Question (canonical):**
[QUESTION_CANONICAL]

**Answer:**
[ANSWER_TEXT]

**Category:** [CATEGORY]
**Subcategory:** [SUBCATEGORY]
**Tags (comma-separated, lowercase):** [TAGS_CSV]

**Certifications referenced (comma-separated, e.g. SOC2_TYPE2, ISO27001):**
[CERTIFICATIONS_REFERENCED_CSV]

**Evidence attachments (one URL per line):**
[EVIDENCE_ATTACHMENT_URLS]

**Approved by (email):** [APPROVED_BY_EMAIL]
**Approved date (ISO-8601, UTC):** [APPROVED_DATE_ISO]

---

## Style reminders

- Keep answers concise. Aim for 2-4 sentences unless the question truly requires more.
- State verifiable facts only. No marketing adjectives ("industry-leading", "best-in-class", "robust").
- Do not promise features that are roadmap-only. If the feature is planned, say so and include the approximate quarter only if public.
- Do not include customer names, dollar amounts, or pricing specifics unless the matching `pricing_reference_ids` are populated and the category is `commercial`.
- Prefer active voice. Prefer present tense for current capability.
- When citing a control or certification, name it precisely (e.g. "SOC 2 Type II" not "SOC 2 certified").
- When a nuance differs by jurisdiction, write one answer per jurisdiction rather than a hedged single answer.

## Submission checklist

- [ ] Placeholders replaced
- [ ] Category matches the enum in `references/answer-bank-schema.md`
- [ ] Approver email is a valid @contoso.com address
- [ ] No competitor names
- [ ] No unreleased product claims
- [ ] Evidence links resolve

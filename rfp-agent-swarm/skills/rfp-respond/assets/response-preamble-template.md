# LOW-Confidence Response Preamble

Attached verbatim to the top of every LOW-tier (generated) response before it
is written to `working/responses.json`. Non-negotiable; `rfp-gates` checks
for its presence on every LOW row.

## Preamble block

> The following response was generated based on [SOURCE_SUMMARY]. It has
> been flagged for SME review before submission. Confidence tier: LOW.
> Reviewer: [REVIEWER_NAME].

## Placeholders

| Placeholder | Filled by | Example |
|---|---|---|
| [SOURCE_SUMMARY] | `draft_responses.py` | "no bank match; generation seeded from related SCIM doc BANK-0118" |
| [REVIEWER_NAME] | `route_to_specialists.py` | "Security Lead" |

## Rules

- Do not reword the preamble.
- Do not omit the preamble for internal / draft-only iterations; it is part of the audit trail.
- If the response is later promoted to HIGH by a reviewer (via `rfp-review`), the preamble is stripped by the reviewer tool, not here.

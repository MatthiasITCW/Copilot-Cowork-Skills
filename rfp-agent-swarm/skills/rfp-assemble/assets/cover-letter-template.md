# Cover Letter — Verbatim Template

Use this template as-is. Substitute every `[PLACEHOLDER]` with the value from
RFP metadata. Do not add marketing language. Do not add additional
paragraphs. Tone: professional, outcome-focused, short.

---

[COMPANY_LEGAL_NAME]
[COMPANY_REGISTRATION]

[SUBMISSION_DATE]

[BUYER_NAME]
Attention: [BUYER_CONTACT]

**Re: Response to [RFP_TITLE] ([RFP_ID])**

Dear [BUYER_CONTACT],

Thank you for the opportunity to respond to [RFP_TITLE]. Please find enclosed
our complete response to the requirements set out in [RFP_ID], submitted on
[SUBMISSION_DATE].

The enclosed package contains:

1. Our response to each requirement, organised in the format you requested.
2. An executive summary highlighting how our approach addresses your stated
   objectives.
3. Supporting appendices for security, technical, and commercial detail.
4. A companion analytics record summarising the basis of each response.

Every response has been reviewed and approved by the relevant subject matter
owner within our organisation prior to submission. Where a response draws on
a specific evidence artefact (certification, audit report, reference
architecture), the artefact is included in the appendices.

Our point of contact for any clarifications during your evaluation is:

- Name: [ACCOUNT_EXECUTIVE_NAME]
- Email: [ACCOUNT_EXECUTIVE_EMAIL]

We would welcome the opportunity to discuss our submission with your team.
We will respond to any clarification request within two business days.

We confirm that this submission is valid for the period specified in the
RFP and is offered in accordance with the terms set out therein.

Yours faithfully,

[SIGNATORY_NAME]
[SIGNATORY_TITLE]
[COMPANY_LEGAL_NAME]

---

## Placeholder Reference

| Placeholder | Source |
|:---|:---|
| `[BUYER_NAME]` | RFP metadata `buyer_name` |
| `[BUYER_CONTACT]` | RFP metadata `buyer_contact` |
| `[RFP_TITLE]` | RFP metadata `rfp_title` |
| `[RFP_ID]` | RFP metadata `rfp_id` |
| `[SUBMISSION_DATE]` | RFP metadata `submission_date` |
| `[ACCOUNT_EXECUTIVE_NAME]` | RFP metadata `account_executive_name` |
| `[ACCOUNT_EXECUTIVE_EMAIL]` | RFP metadata `account_executive_email` |
| `[SIGNATORY_NAME]` | RFP metadata `signatory_name` |
| `[SIGNATORY_TITLE]` | RFP metadata `signatory_title` |
| `[COMPANY_LEGAL_NAME]` | Branding token `company.legal_name` |
| `[COMPANY_REGISTRATION]` | Branding token `company.registration` |

## Rendering Notes

- Letterhead logo is added by the `pdf` skill from the branding token file —
  the cover letter markdown never references the logo explicitly.
- The footer is the disclaimer footer from
  `/mnt/user-config/.claude/skills/rfp-assemble/assets/disclaimer-footer.md`.
- Do not add a company description paragraph — the executive summary in the
  main deliverable carries that content.

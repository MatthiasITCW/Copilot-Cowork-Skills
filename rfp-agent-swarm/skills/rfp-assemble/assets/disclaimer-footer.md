# Disclaimer Footer — Verbatim

Append this footer to every page of the final PDF deliverable, the cover
letter PDF, and the analytics report when rendered to PDF. Substitute
placeholders with values from branding tokens and RFP metadata.

---

[COMPANY_LEGAL_NAME] | Registration [COMPANY_REGISTRATION] | [CONFIDENTIALITY_LEVEL] | [SUBMISSION_DATE] | Page [PAGE_NUMBER] of [PAGE_COUNT]

Contact: [ACCOUNT_EXECUTIVE_EMAIL]

---

## Placeholder Reference

| Placeholder | Source |
|:---|:---|
| `[COMPANY_LEGAL_NAME]` | Branding token `company.legal_name` |
| `[COMPANY_REGISTRATION]` | Branding token `company.registration` |
| `[CONFIDENTIALITY_LEVEL]` | Branding token `document.confidentiality` (e.g. "Confidential") |
| `[SUBMISSION_DATE]` | RFP metadata `submission_date` |
| `[ACCOUNT_EXECUTIVE_EMAIL]` | RFP metadata `account_executive_email` |
| `[PAGE_NUMBER]` | Auto — injected by PDF renderer |
| `[PAGE_COUNT]` | Auto — injected by PDF renderer |

## Layout

- Font: body font at 8pt
- Colour: `colour.secondary` token
- Alignment: single line centred; email on a second line, right-aligned
- Margin: 10 mm from bottom edge
- Separator: single horizontal rule above the footer in `colour.neutral`

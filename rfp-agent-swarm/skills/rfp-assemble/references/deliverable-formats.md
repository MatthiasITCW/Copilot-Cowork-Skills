# Deliverable Formats

This guide lists every deliverable format `rfp-assemble` supports, the buyer
signals that select each format, the required structure, and the rules for
page limits and attachments. It also contains the decision tree for picking a
format when the buyer allows more than one.

---

## 1. Word (.docx) — Narrative RFP

### When buyer requires it

| Signal in RFP metadata | Typical phrasing |
|:---|:---|
| `required_format: word` | "Respond on our provided Word template" |
| Buyer attaches a `.docx` template | "Please complete the attached document" |
| Buyer expects prose answers of more than 150 words | "Describe in detail…" sections |

### Required structure

| # | Section | Purpose |
|:---:|:---|:---|
| 1 | Cover letter | Imported verbatim from `assets/cover-letter-template.md` |
| 2 | Executive summary | 1 page — outcomes, fit, value |
| 3 | Company overview | Legal entity, history, footprint |
| 4 | Technical response | Product capabilities, integrations, architecture |
| 5 | Security response | SOC 2 / ISO 27001 / GDPR posture; questionnaire answers |
| 6 | Commercial response | Pricing summary (from authorised inputs only) |
| 7 | Case studies | Approved customer references |
| 8 | Appendices | Certifications, diagrams, SLA documents |
| 9 | Provenance appendix | Per-response source / tier / reviewer |

### Rendering

`rfp-assemble` emits a manifest. The `docx` built-in skill renders it. Do not
write `.docx` bytes from Python.

### Page-limit handling

- If RFP metadata sets `page_limit`, the assemble manifest marks any section
  that would exceed the limit as `over_limit: true`.
- The human reviewer must trim before re-running. `rfp-assemble` does not
  silently truncate answers.

### Attachment rules

- Attachments go in an `attachments/` directory inside the final zip.
- The Word file references attachments by filename in the appendix table.

---

## 2. Excel (.xlsx) — Question-per-Row Questionnaire

### When buyer requires it

| Signal | Typical phrasing |
|:---|:---|
| `required_format: excel` | "Complete columns D and E of the attached sheet" |
| Buyer attaches `.xlsx` with questions in rows | Security questionnaires (SIG, CAIQ, VSA, HECVAT) |
| Each answer is short (Yes / No / brief text) | Compliance matrices |

### Required structure

| Column | Purpose |
|:---|:---|
| A | Question ID (as provided by buyer) |
| B | Category |
| C | Question text |
| D | Response (Yes / No / N/A / text) |
| E | Supporting detail / evidence reference |
| F | Provenance: source entry ID |
| G | Provenance: confidence tier |
| H | Provenance: reviewer |

Columns F–H are hidden by default but retained for audit.

### Sheet layout

| Sheet | Contents |
|:---|:---|
| `Summary` | Buyer name, RFP ID, submission date, contact |
| `Security` | All security questions |
| `Technical` | All technical questions |
| `Commercial` | All commercial questions |
| `Company` | Company-overview questions |
| `Provenance` | Every answer with full provenance fields |

### Rendering

The `xlsx` built-in skill renders the manifest into `.xlsx`.

---

## 3. PDF (.pdf) — Flattened Read-Only Deliverable

### When buyer requires it

| Signal | Typical phrasing |
|:---|:---|
| `required_format: pdf` | "Submit a signed PDF" |
| Buyer requires signature / seal | "Signed by authorised signatory" |
| Buyer uploads to a portal that only accepts PDFs | Many public-sector portals |

### Required structure

Same ordering as Word (see Section 1). Output is a single flattened PDF —
bookmarks kept, form fields flattened, fonts embedded.

### Rendering

Two paths:

| Path | When to use |
|:---|:---|
| Word → PDF | When narrative formatting matters; render Word first, then use `pdf` skill to flatten |
| Direct PDF | When buyer supplies a PDF form to fill |

### Signature footer

Every page must carry the disclaimer footer (see
`/mnt/user-config/.claude/skills/rfp-assemble/assets/disclaimer-footer.md`).
The footer contains company legal name, registration, confidentiality level,
submission date, and page N of M.

---

## 4. Portal CSV / JSON / XML

Three major buyer portals are supported. The portal format is selected via
`required_format: portal` plus a `portal_vendor` field in RFP metadata.

### 4.1 Ariba — CSV Import

| Column | Description |
|:---|:---|
| `question_id` | Ariba question identifier |
| `response` | Answer text |
| `comment` | Reviewer notes |
| `attachment_filename` | Filename only; file travels alongside the CSV |
| `currency_code` | ISO 4217 — commercial responses only |
| `numeric_value` | For numeric responses only |

Encoding: UTF-8 with BOM. Line endings: CRLF. One row per question.

### 4.2 Coupa — Response JSON

```
{
  "rfpId": "...",
  "responses": [
    {
      "questionId": "...",
      "answerType": "text|yesno|numeric|attachment",
      "value": "...",
      "attachments": ["filename.pdf"],
      "metadata": { "provenance": { "source": "...", "tier": "HIGH" } }
    }
  ]
}
```

Required validation: every `questionId` from the buyer spec must appear exactly
once.

### 4.3 Jaggaer — Response XML

Jaggaer uses a proprietary XML dialect. The manifest includes Jaggaer-specific
field names. Element names follow buyer-supplied XSD exactly — do not
improvise.

### Provenance for portal formats

Portal formats rarely allow embedded provenance. Instead, a side-car file
`manifest.json` is packaged in the final zip alongside the portal file. The
manifest lists every `question_id` with full provenance fields.

---

## 5. Page-Limit Handling (common to all formats)

| Rule | Behaviour |
|:---|:---|
| `page_limit` absent | No limit applied |
| `page_limit` present and fits | Render normally |
| `page_limit` present and exceeded | Mark over-limit sections; stop and ask human to trim |
| Section-level limits (e.g. "exec summary ≤ 1 page") | Enforce per section |

---

## 6. Attachment Rules

| Rule | Detail |
|:---|:---|
| Allowed filetypes | PDF, DOCX, XLSX, PNG, JPG (no executables) |
| Max individual file size | 25 MB (configurable via RFP metadata) |
| Max total package size | 250 MB (configurable) |
| Filename rules | ASCII only, no spaces, kebab-case preferred |
| Virus scan | Performed by caller before packaging (out of scope for this skill) |

---

## 7. Decision Tree — Which Format to Pick

```
                    required_format set?
                      |           |
                     yes          no
                      |           |
                      v           v
              Use that format   multiple allowed?
                                  |       |
                                 yes      no
                                  |       |
                                  v       v
                     buyer template?   Default to Word
                         |   |
                        yes  no
                         |   |
                         v   v
              match template type   signed submission required?
              (word / excel)          |         |
                                     yes        no
                                      |         |
                                      v         v
                                     PDF      portal vendor set?
                                                |         |
                                               yes        no
                                                |         |
                                                v         v
                                       Ariba/Coupa/Jaggaer   Word
```

### Quick lookup table

| Buyer situation | Pick |
|:---|:---|
| Narrative RFP, no template | Word |
| Narrative RFP, Word template attached | Word (from template) |
| Excel questionnaire attached | Excel |
| Signature + seal required | PDF |
| Ariba / Coupa / Jaggaer portal | Portal (CSV / JSON / XML) |
| Mixed (narrative + Excel security annex) | Word primary + Excel annex — produce both |

---

## 8. Known Portal Format Reference

| Portal | Format | Encoding | Notes |
|:---|:---|:---|:---|
| Ariba | CSV | UTF-8 BOM, CRLF | Columns in buyer spec order; numeric fields need `numeric_value` |
| Coupa | JSON | UTF-8 | Wrap in `responses[]`; attachments by filename |
| Jaggaer | XML | UTF-8 | Validate against buyer-supplied XSD |
| SAP Fieldglass | CSV | UTF-8 | Similar to Ariba but different column spec |
| Oracle Sourcing | XML | UTF-8 | Proprietary schema; less common |

If the buyer portal is not in this table, treat it as `word` and attach the
portal file manually — log a request to extend this guide.

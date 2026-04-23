# RFP Metadata Schema

Canonical JSON shape for an RFP record and its questions. Every downstream
skill in the RFP Agent Swarm (rfp-fit-assessment, rfp-respond, rfp-gates,
rfp-review, rfp-assemble) assumes this exact shape. Do not add or rename
fields without coordinating across skills.

In production, records live in Microsoft Dataverse. In the POC they live as
JSON files in `working/`. The contract is the same.

## Top-level RFP record

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rfp_id | string | yes | Generated, format `RFP-YYYY-NNNN` (e.g. `RFP-2026-0042`) |
| buyer_name | string | yes | Legal name as it appears in the document |
| buyer_domain | string | no | Primary web domain, used for Enterprise Search matching |
| rfp_title | string | yes | Document title or subject line |
| issue_date | string (ISO 8601 date) | no | Date RFP was issued to market |
| response_deadline | string (ISO 8601 datetime) | yes | Hard submission deadline with timezone |
| submission_format | enum | yes | One of `portal`, `email`, `file_upload`, `physical` |
| submission_target | string | no | Portal URL, email address, or uploader reference |
| contact_person | object | no | `{ name, title, email, phone }` |
| evaluation_criteria | array of objects | no | `[{ criterion, weight_pct, notes }]` |
| mandatory_attachments | array of strings | no | Named exhibits the buyer requires |
| page_limits | object | no | `{ executive_summary, technical_response, total }` |
| response_language | string | no | ISO 639-1 code, defaults to `en` |
| source_documents | array of strings | yes | Paths of the raw files parsed |
| parse_confidence | enum | yes | `HIGH`, `MEDIUM`, or `LOW` |
| parsed_at | string (ISO 8601 datetime) | yes | When parse_rfp.py ran |
| questions | array of Question | yes | See schema below |
| custom_fields | object | no | Buyer-specific extras that do not fit above |
| notes | string | no | Free-text operator notes |

### Allowed values — submission_format

| Value | Meaning |
|-------|---------|
| portal | Submit via a buyer-hosted portal (Ariba, Coupa, Jaggaer, RFx, SAP Fieldglass, Oracle iSupplier) |
| email | Submit by email to a named address |
| file_upload | Submit via generic file-upload link (Box, Dropbox, SharePoint link) |
| physical | Paper submission, hand delivery or courier |

### Evaluation criteria example

```json
[
  { "criterion": "Security", "weight_pct": 30, "notes": "Pass/fail on SOC 2" },
  { "criterion": "Technical", "weight_pct": 25 },
  { "criterion": "Commercial", "weight_pct": 25 },
  { "criterion": "Company", "weight_pct": 10 },
  { "criterion": "Implementation plan", "weight_pct": 10 }
]
```

## Question schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| question_id | string | yes | Format `Q-NNNN`; sub-parts use suffixes `a`, `b`, `c` |
| section | string | no | Source section heading (e.g. "4.2 Access Controls") |
| page | integer | no | Page number in the source PDF, 1-indexed |
| text | string | yes | Verbatim question text — must not be rewritten |
| text_en | string | no | English translation if source was non-English |
| primary_category | enum | yes | `SEC`, `TEC`, `COM`, `COR`, `GEN` |
| secondary_category | enum | no | Same allowed values as primary_category |
| subcategory | string | no | Free-text subcategory (e.g. "encryption") |
| owner_team | string | yes | Resolved from primary_category |
| mandatory | boolean | yes | True unless explicitly optional |
| word_limit | integer | no | Buyer-specified word limit for the answer |
| word_limit_hint | integer | no | Heuristic suggestion when buyer silent |
| evidence_required | boolean | no | True when the question references an exhibit / attachment |
| credential_check | boolean | no | True when the question asks about a certification |
| pricing | boolean | no | True when the question asks for a price — rfp-respond must not draft a number |
| legal_review | boolean | no | True when the question is a legal redline request |
| translation_required | boolean | no | True when original not in English |
| confidence | enum | yes | `HIGH`, `MEDIUM`, `LOW` on the classification |
| needs_human_triage | boolean | no | True when classifier could not decide |
| notes | string | no | Free-text operator notes |

### Allowed values — owner_team

| Value | Resolved from primary_category |
|-------|-------------------------------|
| Security Engineering | SEC |
| Solution Architecture | TEC |
| Commercial Desk | COM |
| Corporate Marketing | COR |
| Bid Manager | GEN |

## Minimal example

```json
{
  "rfp_id": "RFP-2026-0042",
  "buyer_name": "Northwind Traders",
  "rfp_title": "Cloud Platform RFP 2026",
  "response_deadline": "2026-05-20T17:00:00-05:00",
  "submission_format": "portal",
  "source_documents": ["input/Northwind_RFP_2026_CloudPlatform.docx"],
  "parse_confidence": "HIGH",
  "parsed_at": "2026-04-22T09:14:00Z",
  "questions": [
    {
      "question_id": "Q-0001",
      "section": "4.2 Access Controls",
      "text": "Describe how privileged access to production is granted, reviewed, and revoked.",
      "primary_category": "SEC",
      "owner_team": "Security Engineering",
      "mandatory": true,
      "word_limit": 250,
      "evidence_required": false,
      "confidence": "HIGH"
    }
  ]
}
```

## Storage location

| Environment | Location | Notes |
|-------------|----------|-------|
| POC / local | `working/rfp_metadata.json` and `working/task_list.json` | Idempotent; new runs write incrementing filenames rather than overwriting |
| Production | Dataverse table `rfp_record` with child table `rfp_question` | Same field names, same enums |
| Audit | Immutable copy shipped to SharePoint `/sites/bids/RFP Archive/<rfp_id>/` | Written at end of pipeline |

## Invariants

- `rfp_id` is immutable once assigned.
- `questions[].question_id` is immutable once assigned.
- `text` is verbatim from the source. Never rewrite to fix grammar.
- `parse_confidence = LOW` means no task list is emitted; the record itself
  may still be stored for the audit trail.

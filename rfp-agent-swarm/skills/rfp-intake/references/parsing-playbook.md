# RFP Parsing Playbook

Practical heuristics for turning real-world RFP documents into a clean
`working/rfp_raw.json`. Each section covers a common document shape, what to
expect, and how to handle edge cases. All approaches are non-destructive:
the source file is never modified.

## Word (.docx) RFPs

Most corporate RFPs arrive as Word. Structure is usually:

- Cover page with buyer logo and RFP title.
- Introduction / background section (1-3 pages).
- Instructions (submission format, deadline, Q&A window).
- Evaluation criteria (often a table of weights).
- Questionnaire body — the bulk of the document.
- Appendices (terms and conditions, exhibits).

### Extraction patterns

| Pattern | Indicator | Handling |
|---------|-----------|----------|
| Numbered headings | `1.`, `1.1`, `1.1.1` | Use heading level as `section`; take the trailing text as question only if it ends in `?` or matches a question stem |
| Question stems | starts with "Describe", "Explain", "Provide", "Confirm", "List", "How does", "What is", "Does your" | Treat as a question even without a `?` |
| Question tables | Table with a column called "Question", "Requirement", "Req. ID", or "#" | Each row becomes one question; map ID column to `question_id` |
| Matrix requirements | Table with Yes/No/Partial columns | Each row is a question; `word_limit_hint = 50` |
| Bullet lists under a heading | `Questions:` or `Requirements:` heading | Each bullet becomes one question |
| Inline numbered questions | `Q1.`, `Q2.`, `Question 3:` | Regex `^(Q|Question)\s*\d+` |

### Common gotchas

- Multi-line question text split by Word auto-wrap. Merge lines until the next
  question ID, bullet, or heading.
- Questions embedded inside prose paragraphs. The parser flags these as
  MEDIUM confidence — human spot-check recommended.
- Revision-tracked content. Extraction must ignore rejected revisions; only
  the accepted text counts.

## Excel (.xlsx) RFPs

Most security questionnaires and some full RFPs arrive as workbooks.

### Tab patterns

| Tab name patterns | Meaning |
|-------------------|---------|
| `Security`, `Info Sec`, `CAIQ`, `SIG`, `SIG Lite`, `HECVAT`, `VSA` | All rows route to SEC |
| `Technical`, `Architecture`, `Integration` | All rows route to TEC by default |
| `Commercial`, `Pricing`, `Legal` | All rows route to COM |
| `Instructions`, `Cover`, `Read Me` | Not questions; skip but capture deadlines/contact |
| `Definitions`, `Glossary` | Skip |

### Row patterns

Each question row typically contains:

- ID column (`#`, `Req ID`, `Question ID`, `Control ID`, `Ref`).
- Category or domain column (use as `subcategory`).
- Question text column (`Question`, `Requirement`, `Control`, `Description`).
- Expected response column (`Response`, `Answer`, `Comments`) — left blank by
  the buyer; this is where our answer will eventually land.
- Mandatory column (`Mandatory`, `Required`, `Priority`, `M/O`).

### Handling

- Auto-detect the header row — it is the first row with ≥3 of: an ID-like
  column, a text-like column, a response-like column.
- If a row has no text, it is a heading — emit it as a `section` but not a
  question.
- If a row ID repeats across tabs, treat each as a distinct question; the
  deduper in `build_task_list.py` will collapse true duplicates by text hash.

## PDF RFPs

PDFs split into two worlds:

| Type | Indicator | Handling |
|------|-----------|----------|
| Text-layer PDF | `pdftotext` returns non-empty text | Treat as Word — apply the same heuristics |
| Scanned PDF | `pdftotext` returns empty or garbage | OCR fallback via the pdf built-in skill; confidence drops to at-most MEDIUM |

### Heuristics for text-layer PDFs

- Footer noise (page X of Y, buyer confidential, date) is stripped by pattern.
- Two-column layouts are detected by coordinate clustering; the parser reads
  left column fully then right column to preserve question order.
- PDF form fields are inspected — some RFPs use interactive forms where each
  field label is a question.

### Scanned PDFs

- Run OCR first (pdf built-in).
- Expected degradation: ligatures, bullet characters, table alignment.
- Never emit HIGH confidence from a scanned source — cap at MEDIUM.
- If OCR word-error-rate appears high (heuristic: >5% of tokens contain no
  vowels), set LOW and escalate.

## Buyer portal exports

Ariba, Coupa, Jaggaer, RFx and SAP Fieldglass all export questionnaires as
CSV or XLSX. The quirk is column naming.

| Portal | Typical ID column | Typical text column | Notes |
|--------|-------------------|---------------------|-------|
| Ariba Sourcing | `Question Number` | `Question` | Nested sub-questions use `1.1.1` |
| Coupa | `Number` | `Question Text` | Requirements in a separate sheet |
| Jaggaer | `Question ID` | `Question` | Often tab-delimited |
| RFx (various) | `Ref` | `Description` | Mandatory flag in `Mandatory` column |
| SAP Fieldglass | `Item` | `Text` | Less common for RFPs |

Pass the correct column mapping explicitly:

```
python scripts/parse_rfp.py input/coupa_export.csv \
    --id-column "Number" --text-column "Question Text" \
    --output working/rfp_raw.json
```

## Known questionnaire templates

| Template | Typical size | Format | Notes |
|----------|--------------|--------|-------|
| SIG Lite | ~330 questions | xlsx | Latest version preferred; versions shift row counts |
| SIG Core | ~1000+ questions | xlsx | Usually only requested by large financial buyers |
| CAIQ v4 | ~261 questions | xlsx | Cloud Security Alliance; Yes/No/NA with commentary |
| VSA Full | ~260 questions | xlsx | Shared Assessments variant |
| HECVAT Full | ~250 questions | xlsx | Higher ed; HECVAT Lite is a reduced version |
| HECVAT Lite | ~70 questions | xlsx | |

When one of these templates is detected (by header fingerprint), the parser
tags `template_detected` in metadata and pre-fills expected counts so count
mismatches become visible immediately.

## Buyer block extraction

The buyer block appears in the first ~2 pages or in the cover sheet of a
workbook. Heuristics:

- `buyer_name` = first proper-noun phrase near "issued by", "prepared by",
  "submitted to". Fall back to the cover logo's alt text if embedded.
- `contact_person` = nearest block containing an email address and a phone.
- `response_deadline` = date nearest the phrase "due", "deadline",
  "submission deadline", "closing date". Multiple candidates are all kept
  in `deadline_candidates`; the operator confirms the final.
- `submission_format` = detected from keywords "via portal", "email to",
  "upload to", "hand deliver".

## Confidence scoring

| Level | Criteria |
|-------|----------|
| HIGH | All of: non-empty questions array, every question has `text` non-empty, question count within ±5% of any detected template's expected count, `response_deadline` parsed, `buyer_name` non-empty |
| MEDIUM | Any one of: 5-20% count mismatch, some questions have missing IDs, deadline ambiguous, two-column parsing fell back |
| LOW | Any one of: scanned PDF with high OCR error rate, no questions detected, >20% count mismatch, no buyer block found |

On LOW, the pipeline stops. The intake skill emits a Teams message to the
bid manager with a link to the source document and does not create a task
list.

## Do not

- Do not rewrite question text for grammar, clarity, or tone. The buyer's
  words are evidence.
- Do not drop a question because its wording is unclear. Tag it for human
  triage instead.
- Do not guess a deadline. If none is extractable, leave it null and flag.
- Do not merge questions across tabs just because the text looks similar.
  Dedup is the job of `build_task_list.py` and uses a deterministic hash.

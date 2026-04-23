---
name: rfp-respond
description: Drafts first-pass answers to every RFP question using a strict retrieval-first pattern, routes questions to Security / Technical / Commercial teams in parallel, and stamps every response with a confidence tier and provenance before handing off to quality gates.
when_to_use: After rfp-intake has produced a task list and rfp-fit-assessment has returned a GO decision. Use this skill when drafting, not when editing, finalising, or assembling the final document.
version: 1.0.0
---

# rfp-respond — Step 3: Parallel Team Processing

Retrieval-first drafting with confidence tiers, team routing, and built-in guardrails.

## 1. Purpose

This skill is the execution engine for Step 3 of the RFP Agent Swarm workflow. It converts a parsed, routed task list into a `responses.json` artifact in which every question carries a draft answer, a confidence tier (HIGH / MEDIUM / LOW), a source reference, and a reviewer flag where relevant.

It is built around one non-negotiable principle: retrieval over generation. For every question the answer bank (`rfp-answer-bank`) is searched first. Only if no acceptable match exists does the system generate — and when it does, the answer is flagged, capped at 75 confidence, and never shipped without human review.

It is the only skill in the swarm that writes answer text. Downstream skills verify, assemble, and submit; they do not re-draft.

## 2. When to Use

Trigger phrases (≥8):

- "draft RFP responses"
- "answer RFP questions"
- "write the security section"
- "respond to this questionnaire"
- "fill in the RFP answers"
- "draft security questionnaire responses"
- "answer the technical questions"
- "complete the commercial section"
- "run team drafting"
- "generate first-pass responses"

### Do NOT use for…

| Situation | Use instead |
|---|---|
| Parsing the incoming RFP PDF / DOCX | `rfp-intake` |
| Go / No-Go decision | `rfp-fit-assessment` |
| Updating the Loopio → AI Search answer bank | `rfp-answer-bank` |
| Post-draft quality scoring and automated checks | `rfp-gates` |
| Sending to SME / reviewer queues and tracking sign-off | `rfp-review` |
| Producing the branded, submittable final document | `rfp-assemble` |
| Generating pricing figures from scratch | Pricing desk (human); this skill only **structures** authorised inputs |
| Signing off legal redlines | `legal-review` + counsel; this skill **flags** only |

## 3. Inputs

| Input | Source | Format | Required |
|---|---|---|---|
| Task list | `rfp-intake` output | `working/task_list.json` | Yes |
| Bank search results | `rfp-answer-bank/scripts/search_bank.py` (one call per question) | `working/bank_search_results.json` | Yes |
| GO decision | `rfp-fit-assessment` output | `working/fit_assessment.json` with `decision: "GO"` | Yes |
| Authorised pricing inputs | Commercial Lead (human) | `working/pricing_inputs.json` (optional per-question) | Conditional |
| Legal playbook pointer | `legal-review` skill | Reference only | Yes |

If any required input is missing the skill halts and emits a structured error naming the missing artefact. It never invents inputs.

## 4. Outputs

| Output | Path | Consumer |
|---|---|---|
| Drafted responses | `working/responses.json` | `rfp-gates`, `rfp-review` |
| Team queue manifest | `working/team_queues.json` | Parallel team agents |
| Per-question confidence record | `working/confidence.json` | `rfp-gates` (for audit) |
| Progress card | Inline Adaptive Cards | User (live progress) |
| Low-confidence preamble block | Injected from `assets/response-preamble-template.md` | Response text itself |

`responses.json` schema (one row per question):

```
{
  "question_id": "Q-042",
  "team": "security",                     // security | technical | commercial
  "consulted_teams": ["technical"],
  "tier": "MEDIUM",                       // HIGH | MEDIUM | LOW
  "confidence": 82,                       // 0-100, capped at 75 if generated
  "response_text": "…",
  "source": {
    "bank_entry_id": "BANK-0917",
    "last_approved_date": "2026-02-11",
    "original_question": "…",
    "delta_summary": "tightened wording; scoped to EU data residency"
  },
  "flags": ["REVIEWER_REQUIRED"],
  "reviewer_required": true
}
```

## 5. Retrieval-First Workflow

```
 For each question in task_list.json:
   │
   ├── 1. Call rfp-answer-bank/scripts/search_bank.py
   │       (hybrid: keyword + vector + semantic reranker)
   │
   ├── 2. scripts/confidence_scorer.py → tier + confidence
   │
   ├── 3. Decision tree (scripts/draft_responses.py):
   │        HIGH   → verbatim reuse; log source
   │        MEDIUM → adapt within allowed edits (see playbook)
   │                 record delta_summary
   │        LOW    → emit placeholder + FLAG_FOR_GENERATION
   │                 cap confidence ≤ 75
   │                 attach preamble (assets/)
   │
   ├── 4. scripts/route_to_specialists.py assigns PRIMARY team
   │       and CONSULTED teams
   │
   └── 5. Append row to working/responses.json (atomic write)
```

See `references/retrieval-first-playbook.md` for the full playbook including query formulation rules, re-query triggers, and worked examples for each tier.

## 6. Confidence Tiers

| Tier | Reranker score | Action | Cap | Review path |
|---|---|---|---|---|
| HIGH | ≥ 0.90 | Verbatim reuse | 100 | Light verification in `rfp-review` |
| MEDIUM | 0.75 – 0.89 | Adapt (tighten / scope) | 89 | Standard review; reviewer verifies the delta |
| LOW | < 0.75 | Generate with caveats | **75** | Mandatory SME review; flagged |

Rules enforced by `scripts/confidence_scorer.py`:

1. No generated response may exceed 75 confidence, ever.
2. Only a human (via `rfp-review`) may promote a tier.
3. Every response carries `bank_entry_id` (or `GENERATED`) and `last_approved_date`.

Full rules and rationale: `references/confidence-tier-rules.md`.

## 7. Team Routing Matrix

| Question signal | Primary team | Agents | Consulted |
|---|---|---|---|
| SOC 2, ISO 27001, penetration test, encryption, SIG, CAIQ, HECVAT | Security | Security Questionnaire agent + Compliance Analyst | Technical |
| API, SSO, SCIM, deployment, architecture, SLA, uptime | Technical | Product Capabilities + Integration Specialist | Security |
| Pricing, commercial terms, references, case study, company history, MSA, DPA | Commercial | Pricing Specialist + Legal Review Agent + company overview / case studies | Security (for DPA), Technical (for SLA in MSA) |
| Multi-tagged (e.g. "describe your SSO security model") | Shared queue → Security PRIMARY, Technical CONSULTED | both | — |

Routing is deterministic, driven by tags emitted by `rfp-intake`. See `references/team-specialist-guides.md` for per-agent responsibilities and handoff rules.

## 8. Guardrails

| Guardrail | Enforced by |
|---|---|
| Never fabricate certifications, audit dates, customer names | `confidence_scorer.py` caps generated at 75 + flag; `team-specialist-guides.md` rule |
| Never generate pricing figures | `route_to_specialists.py` rejects pricing questions without `pricing_inputs.json` |
| Never sign off legal terms | Legal Review Agent flag = `HUMAN_APPROVAL_REQUIRED` always |
| No tier promotion by agents | `confidence_scorer.py` deterministic; only humans promote |
| No new claims in MEDIUM adaptation | Allowed-edits list in `retrieval-first-playbook.md`; `draft_responses.py` records delta for audit |
| No marketing fluff | `tone-and-style-guide.md` banned-phrase list |

## 9. How to Invoke

```
# 1. Route (partitions task list into team queues)
python scripts/route_to_specialists.py \
  --task-list working/task_list.json \
  --output working/team_queues.json

# 2. Score each bank search result
python scripts/confidence_scorer.py \
  --search-result working/bank_search_results.json \
  --output working/confidence.json

# 3. Draft
python scripts/draft_responses.py \
  --task-list working/task_list.json \
  --bank-search-results working/bank_search_results.json \
  --output working/responses.json
```

All three emit JSON to stdout as well as the `--output` path, so they chain cleanly in Copilot Studio flows.

Progress card (rendered inline):

- Per-team progress: Security N/M, Technical N/M, Commercial N/M
- Confidence distribution donut (HIGH / MEDIUM / LOW counts)
- Flag count (reviewer_required = true)

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| All questions scored LOW | Bank search returned no matches; check reranker is enabled in `rfp-answer-bank` call | Re-run `search_bank.py` with `--semantic-reranker on`; confirm index is populated |
| MEDIUM answers rejected downstream by `rfp-gates` | Delta summary missing or edits exceed allowed list | Check `draft_responses.py` output for `delta_summary`; see allowed-edit list in `retrieval-first-playbook.md` |
| Generated response exceeds 75 confidence | Bypassed `confidence_scorer.py` or manual edit | Re-run scorer; never edit `confidence` field by hand |
| Pricing question returns empty response | No `pricing_inputs.json` supplied | Request authorised inputs from Commercial Lead; do not generate |
| Team queues unbalanced (Security at 80%, others idle) | Tags mis-assigned upstream in `rfp-intake` | Re-run `rfp-intake` tagging step; do not rebalance in this skill |
| Legal response appears but `reviewer_required=false` | Legal flag not applied | Bug in `route_to_specialists.py` — every legal question must carry `HUMAN_APPROVAL_REQUIRED` |
| Duplicate `question_id` rows in `responses.json` | Multi-team question written twice (primary + consulted) | Only PRIMARY owner writes the row; consulted teams contribute via notes field |
| `responses.json` has questions from task list missing | Skill halted mid-run | Check stderr for the missing-input error; re-run, writes are idempotent by `question_id` |

## Built-In Skills Used

| Cowork Skill | How this skill uses it |
|---|---|
| Excel | Append rows to `output/rfp-<rfp_id>/audit-log.xlsx`; read any authorised pricing input workbook supplied by the Commercial Lead |
| Adaptive Cards | Render the live per-team progress dashboard, KPI row on batch completion, confidence-tier donut, and flagged-questions table |
| Enterprise Search | Fallback when the answer bank returns no acceptable match — broadens the search across approved enterprise sources before falling through to generation |
| Deep Research | Escalated path for novel technical questions where neither the bank nor enterprise search yields grounded material |
| Word | Read reference material (playbooks, MSA templates, security whitepapers) cited by the specialist teams while drafting |
| PDF | Read attached RFP exhibits and prior-submission PDFs used as grounding context |
| Communications | Brief the team leads (Security / Technical / Commercial) on flagged items and batch completion |

## Audit Log

Every meaningful step of the drafting run is appended to `output/rfp-<rfp_id>/audit-log.xlsx` via the shared Excel skill. This gives `rfp-gates` and `rfp-review` a complete, replayable record of what the swarm decided and why.

| Event Type | When | Actor | Key fields |
|---|---|---|---|
| `RESPONSE_DRAFT_STARTED` | A batch of drafting begins | AI | `team` (Security/Technical/Commercial), `batch_size` |
| `KB_MATCH_FOUND` | Answer bank returns a match for a question | AI | `question_id`, `kb_entry_id`, `tier` (HIGH/MEDIUM/LOW), `reranker_score` |
| `RESPONSE_GENERATED` | No KB match — AI generates a response | AI | `question_id`, `confidence` (capped 0.75), `flag_reason` |
| `TEAM_ROUTED` | Question routed to specialist team | AI | `question_id`, `team`, `reason` |
| `RESPONSE_BATCH_COMPLETE` | A team's batch finishes | AI | `team`, `total`, `tier_distribution` |

Schema and append helper:

- [audit-log-schema.md](../rfp-answer-bank/references/audit-log-schema.md) — canonical column order, enums, and validation rules
- [append_audit.py](../rfp-answer-bank/scripts/append_audit.py) — idempotent appender used by every RFP skill

Every response row ALSO carries a `provenance_id` (either the matched `kb_entry_id` or the literal string `generated+needs_review`). That `provenance_id` is preserved verbatim through `rfp-gates`, `rfp-review`, and `rfp-assemble` so the final deliverable can be traced, row-for-row, back to an approved bank entry or a flagged generation event.

## Adaptive Card Dashboard

Rendered inline via the Cowork Adaptive Cards built-in skill. The card is refreshed as each team's batch progresses so reviewers can watch the swarm work in real time.

Live progress card (refreshed as drafts complete):

- Three per-team progress bars — Security, Technical, Commercial — each showing `% complete` and a rolling ETA based on current throughput
- Current batch size and elapsed time per team

On batch complete, the card expands to include:

- KPI row — total drafted, HIGH %, MEDIUM %, LOW/flagged %
- Donut — confidence tier distribution across the full run
- Table — flagged questions (LOW tier + any generated response): `question_id`, `team`, `reason`, `preview` (first 140 chars)
- Call-to-action button — **"Run the three quality gates"** which invokes `rfp-gates`

The card is the primary human touch point for the drafting step; everything it shows is also written to `responses.json` and the audit log, so nothing displayed here is a separate source of truth.

## 11. Related Skills

### RFP chain

`rfp-intake` → `rfp-fit-assessment` → **THIS SKILL (`rfp-respond`)** → `rfp-gates` → `rfp-review` → `rfp-assemble`

`rfp-answer-bank` sits underneath the entire chain as the shared substrate — every drafting, gating, and review decision resolves through it.

This skill is the **heavy-compute step** in the chain. It reads the task list from `rfp-intake`, queries `rfp-answer-bank` on every single question (retrieval-first), stamps each row with a `provenance_id` (KB entry or `generated+needs_review`), and then hands off a complete `responses.json` to `rfp-gates`. No other skill in the chain writes answer text; no other skill fans out across three specialist teams in parallel.

### Cowork built-ins leveraged

- **Excel** — append to the run's `audit-log.xlsx`; read any authorised pricing input workbook
- **Adaptive Cards** — render the live progress dashboard, KPI row, tier donut, and flagged-questions table
- **Enterprise Search** — fallback retrieval when the answer bank misses, before falling through to generation
- **Deep Research** — escalation path for novel technical questions that neither the bank nor enterprise search can ground
- **Word / PDF** — read reference material (playbooks, MSAs, whitepapers, prior-submission exhibits) cited while drafting
- **Communications** — brief team leads on flagged items and notify them when a batch completes

### Peer and chain skills

| Skill | Relationship |
|---|---|
| `rfp-intake` | Upstream — produces the task list this skill consumes |
| `rfp-fit-assessment` | Upstream — GO decision is a precondition |
| `rfp-answer-bank` | Substrate — this skill calls its `search_bank.py` on every question; also consumes its `append_audit.py` and `audit-log-schema.md` |
| `rfp-gates` | Downstream — consumes `responses.json` and the audit log for automated QA |
| `rfp-review` | Downstream — handles flagged items and tier promotion |
| `rfp-assemble` | Downstream — builds final deliverable from approved responses |
| `legal-review` | Peer — Legal Review Agent within this skill defers to it for redline playbook |

## 12. File Index

| File | Purpose |
|---|---|
| `references/retrieval-first-playbook.md` | Query formulation, adaptation rules, worked examples |
| `references/confidence-tier-rules.md` | Thresholds, capping, provenance, override policy |
| `references/team-specialist-guides.md` | Per-team agent responsibilities, rules, handoffs |
| `references/tone-and-style-guide.md` | Voice, concision targets, banned phrases |
| `scripts/draft_responses.py` | Core drafting orchestrator |
| `scripts/confidence_scorer.py` | Tier + confidence assignment |
| `scripts/route_to_specialists.py` | Team queue partitioning |
| `assets/response-preamble-template.md` | LOW-tier preamble block |

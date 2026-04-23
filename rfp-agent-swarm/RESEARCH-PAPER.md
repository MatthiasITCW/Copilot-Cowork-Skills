# The RFP Skill Swarm — Research Paper

*An architectural study of agentic skill composition in Microsoft 365 Copilot Cowork.*

> **Plain-text mirror** of the working research paper that informs the [RFP Agent Swarm README](README.md). This file is the long-form companion; the README is the curated overview.

---

**Scope.** Seven custom Cowork skills — `rfp-intake`, `rfp-fit-assessment`, `rfp-answer-bank`, `rfp-respond`, `rfp-gates`, `rfp-review`, `rfp-assemble` — composed into an end-to-end Request-for-Proposal response pipeline.

**Date of analysis.** 23 April 2026.

---

## Abstract

This paper documents an architectural pattern observed in a working set of seven custom skills deployed within Microsoft 365 Copilot Cowork. The skills — collectively the "RFP Skill Swarm" — automate the response lifecycle for Requests for Proposal (RFPs), Requests for Information (RFIs), and Requests for Quotation (RFQs). The swarm comprises 7 `SKILL.md` packages, 22 Python scripts, 26 reference documents, and 10 reusable assets. We verified that all 22 scripts pass syntax compilation, expose well-formed `argparse` command-line interfaces, and use only the Python standard library — making them fully portable inside Cowork's sandboxed runtime. The paper identifies six recurring architectural patterns: skill-as-orchestration-layer, working-directory blackboard, retrieval-first generation, confidence-tier propagation, non-overridable human gates, and append-only audit trails. We argue these patterns generalise to any agentic workflow that must combine large-language-model reasoning with deterministic computation and human accountability.

## Executive Summary

Cowork is Microsoft's agentic productivity layer for Microsoft 365. It augments Copilot with custom skills — Markdown bundles that an LLM agent loads on demand to extend its capabilities. The RFP Skill Swarm pushes this model further than a typical single-skill use case: it composes seven specialised skills into a directed acyclic workflow that ingests an RFP document, qualifies the opportunity, drafts answers from a curated knowledge base, gates them through legal and security approval, captures human corrections, and assembles a buyer-format submission package. Each skill is independent, narrowly scoped, and connects to its neighbours through structured JSON files written to a shared working directory.

The deterministic backbone is a set of 22 Python scripts that handle parsing, classification, scoring, retrieval, and document assembly. The probabilistic surface — LLM judgment — is reserved for tasks where retrieval fails or human nuance is required: medium-confidence answer adaptation, low-confidence generation, and synthesis of novel research. Critically, all human approval gates are non-overridable: there is no force flag, no bypass token, and no automation path that crosses an unapproved gate. This combination of deterministic scripting, retrieval-grounded generation, and structurally enforced human accountability is what makes the swarm trustworthy enough to handle commercial bids.

---

## 1. Introduction

### 1.1 Microsoft 365 Copilot Cowork

Cowork is a preview of Microsoft 365 Copilot that allows users to extend Copilot with custom skills stored in OneDrive at `/Documents/Cowork/Skills/`. A Cowork skill is a folder containing a `SKILL.md` manifest with YAML frontmatter (name, trigger description) and optional sub-folders: `references/` for on-demand Markdown lookup tables, `scripts/` for deterministic Python processing, and `assets/` for static templates inserted verbatim. At runtime an underlying agent reads the `SKILL.md`, decides whether the user's query matches the trigger phrases, and follows the operational instructions embedded in the Markdown.

Crucially, Cowork skills are not simple prompt templates. A skill can invoke its own Python scripts, read from references on demand, write structured output files, and call any built-in capability the host exposes — Word, Excel, PowerPoint, PDF, Adaptive Cards, Outlook, Teams, SharePoint, OneDrive, Enterprise Search, and Deep Research. This creates a programming model where the skill author composes deterministic code, declarative templates, and LLM reasoning into a single workflow the agent executes.

### 1.2 Why RFPs?

RFP response is a high-stakes, high-effort knowledge task. A single enterprise RFP may contain 200–500 questions distributed across security, technical, commercial, legal, and corporate domains. Responses must be accurate, defensible against audit, compliant with internal authorisation matrices, and delivered in a buyer-prescribed format. The work spans multiple specialists, several days, and a complex web of approval. It is the kind of workflow that exposes every weakness of naive AI automation — hallucinated certifications, fabricated audit dates, unauthorised pricing, and unreviewed legal commitments.

The RFP Skill Swarm directly addresses these failure modes by partitioning the work into seven skills, each with narrow responsibility and explicit hand-offs.

### 1.3 Methodology

This study examined the seven RFP skills installed in a personal Cowork skills folder. For each skill we read the full `SKILL.md`, inventoried its references and assets, and audited every Python script via syntax compilation, import inspection, and command-line interface verification. We executed representative scripts end-to-end with synthetic input data to confirm runtime behaviour. We then synthesised the workflow DAG, the shared-state model, and the human-checkpoint pattern across the swarm.

---

## 2. Inventory and Script Audit

### 2.1 Skill inventory

| Skill | Scripts | References | Assets | Primary purpose |
|---|---:|---:|---:|---|
| `rfp-intake` | 3 | 3 | 1 | Parse, classify, deduplicate RFP questions into a task list |
| `rfp-fit-assessment` | 3 | 3 | 1 | Weighted scorecard and Go/No-Go memo for human decision |
| `rfp-answer-bank` | 6 | 5 | 2 | Hybrid-search KB substrate; hosts shared audit log |
| `rfp-respond` | 3 | 4 | 1 | Retrieval-first drafting routed by team specialism |
| `rfp-gates` | 3 | 4 | 2 | Three non-overridable approval gates (Security, Legal, Pricing) |
| `rfp-review` | 3 | 3 | 1 | Human review queue and structured correction capture |
| `rfp-assemble` | 3 | 4 | 2 | Buyer-format submission package and Record Set |
| **Total** | **22** | **26** | **10** | |

### 2.2 Script audit results

| Check | Result |
|---|---|
| Syntax compilation (`py_compile`) on all 22 scripts | 22 / 22 PASS |
| Standard-library imports only (no `pip install` required) | 22 / 22 PASS |
| `argparse` CLI exposed and `--help` returns valid usage | 22 / 22 PASS |
| End-to-end execution with sample data (4 representative scripts) | 4 / 4 PASS |
| Defensive schema validation with structured error output | Confirmed across all tested scripts |

All scripts import only from the Python standard library: `argparse`, `json`, `pathlib`, `datetime`, `re`, `sys`, `typing`, `dataclasses`, `csv`, `hashlib`, `zipfile`, `uuid`, `collections`, `statistics`, `math`, `os`, `glob`, and `__future__` annotations. **Zero third-party dependencies.** This is significant: it means the swarm runs unchanged in any Python 3.8+ sandbox without dependency resolution, network access, or vendoring.

When invoked with a malformed payload, scripts emit a structured JSON error (for example, `compute_fit_score.py` returned `{"error": "scores missing dimensions: [...]"}` rather than crashing with a Python traceback). This defensive design protects the agent loop: the LLM can read the error JSON, reason about the missing field, and self-correct without surfacing internal failures to the user.

---

## 3. Skill Specifications

Each skill below is documented with the same template: trigger phrases, purpose, inputs, outputs, scripts, and hand-off.

### 3.1 `rfp-intake`

Trigger phrases include *"a new RFP came in, can you parse it"*, *"intake this proposal"*, *"classify RFP questions"*, *"process this tender"*, *"what's in this RFP, give me the summary"*.

- **Purpose** — Ingest, parse, and classify an incoming RFP/RFI/RFQ document into a deduplicated task list, routed by team (Security, Technical, Commercial, Company, General).
- **Inputs** — Unstructured Word/Excel/PDF in `input/`. No upstream skill required (this is the first-touch skill).
- **Outputs** — `working/rfp_raw.json`, `working/classified.json`, `working/task_list.json`, `output/<rfp_id>_TaskList.xlsx`, an Adaptive Card summary, and audit events.
- **Scripts** — `parse_rfp.py` extracts questions and metadata; `classify_questions.py` applies the taxonomy; `build_task_list.py` deduplicates and merges into the canonical list.
- **Hand-off** — Passes `working/task_list.json` to `rfp-fit-assessment`.

### 3.2 `rfp-fit-assessment`

Trigger phrases include *"should we bid on this"*, *"go/no-go analysis"*, *"fit score this RFP"*, *"qualify this RFP"*, *"build the Go/No-Go memo for leadership"*.

- **Purpose** — Produce a one-page advisory memo via a weighted scorecard across seven dimensions (KB match, technical, commercial, competitive, strategic, resource, deadline). The system never decides; it surfaces evidence.
- **Inputs** — `working/task_list.json`, historical KB match statistics from `rfp-answer-bank`, human-supplied dimension scores anchored to a 0–5 rubric.
- **Outputs** — `working/kb_match_estimate.json`, `working/fit_result.json`, `working/go_no_go_memo.md`, `working/fit_scorecard.xlsx`, and an Adaptive Card with decision action buttons.
- **Scripts** — `kb_match_estimator.py` looks up prior match rates; `compute_fit_score.py` validates that weights sum to 100 and computes the band; `generate_go_no_go_memo.py` performs strict template substitution (no free-form LLM rewriting).
- **Hand-off** — Only after a `HUMAN_DECISION_LOGGED` audit event does control pass to `rfp-respond`. A *Conditional* decision invokes a clarification meeting; a *No-Go* declines politely and logs lessons for next time.

### 3.3 `rfp-answer-bank`

Trigger phrases include *"search the answer bank"*, *"add to KB"*, *"sync Loopio export"*, *"merge corrections into KB"*, *"search our RFP library"*. This skill is also called programmatically by the other six.

- **Purpose** — The shared retrieval substrate and audit-log host. Manages a hybrid (BM25 + vector + semantic reranker) Azure AI Search index, routes corrections from `rfp-review` back into the KB, and owns the canonical audit-log schema used by every other skill.
- **Outputs** — Azure AI Search index, structured search results with confidence tiers (HIGH ≥ 0.90, MEDIUM 0.75–0.89, LOW < 0.75), sync and merge reports, and the shared `output/rfp-<rfp_id>/audit-log.xlsx` workbook.
- **Scripts** — `search_bank.py` runs the hybrid query; `add_entry.py` validates and versions new entries; `sync_loopio_export.py` diffs against the current bank; `merge_corrections.py` is idempotent and refuses missing reviewer signatures; `append_audit.py` is the **sole writer** to the audit log; `render_audit_dashboard.py` exports the audit timeline.
- **Critical guardrails** — Never fabricate an entry, never auto-merge without reviewer sign-off, never return deprecated entries, never hard-delete (only deprecate with a `replaces[]` pointer), never quote a LOW-tier result, never let generated content claim HIGH.

### 3.4 `rfp-respond`

Trigger phrases include *"draft RFP responses"*, *"answer RFP questions"*, *"write the security section"*, *"complete the commercial section"*, *"run team drafting"*.

- **Purpose** — Convert the task list into tiered draft responses via a strict retrieval-first decision tree. Search answer-bank on every question; use HIGH-tier matches verbatim; lightly adapt MEDIUM matches within an allowed-edits list; generate and flag LOW results.
- **Outputs** — `working/responses.json` with per-question tier, confidence, source, flags, and delta summary; `working/team_queues.json` partitioning questions for Security, Technical, and Commercial; an Adaptive Card with a tier donut and flagged-questions table.
- **Scripts** — `route_to_specialists.py` applies deterministic team routing; `confidence_scorer.py` applies reranker thresholds and tier caps; `draft_responses.py` orchestrates the retrieval-first decision tree.
- **The 75-cap rule** — No generated response may exceed 75 confidence, ever. Only a human reviewer may promote a tier. `confidence_scorer.py` is deterministic and refuses to upgrade scores; this rule propagates downstream through gates, review, and assembly.

### 3.5 `rfp-gates`

Trigger phrases include *"run quality gates"*, *"security gate check"*, *"legal review gate"*, *"pricing approval gate"*, *"send for gate approval"*.

- **Purpose** — Orchestrates three non-negotiable approval gates — Security Completeness, Legal Review, and Pricing Approval — before responses can proceed to assembly. Prepares an evidence pack for each gate and dispatches an Adaptive Card approval request to the named approver.
- **Scripts** — `run_gates.py` executes automated prechecks and exits non-zero if a blocker is found; `send_gate_approval.py` builds the per-gate Adaptive Card payload; `gate_status_tracker.py` aggregates approver responses into a verdict that PASSes only if all three gates are Approved.
- **Critical guardrails** — Hard gates **cannot** be overridden: no force flag, no bypass token, deadline pressure does not unlock. Each gate has one named approver. Approvals capture identity and timestamp. Rejections are immutable audit events; re-submission and approval appear as separate rows.

### 3.6 `rfp-review`

Trigger phrases include *"review flagged RFP items"*, *"correct RFP responses"*, *"capture corrections"*, *"review low-confidence answers"*, *"start reviewer queue"*.

- **Purpose** — Surface only the items that need human attention. Capture every correction with a structured reason from a controlled enum, and feed corrections back into `rfp-answer-bank` to close the learning loop.
- **Scripts** — `build_review_queue.py` applies a six-tier prioritisation (FAIL > LOW > MEDIUM+delta > missing-mandatory > sensitive > WARN); `log_correction.py` validates the reason enum and appends to the corrections JSONL; `export_corrections.py` rolls up the JSONL into the format `rfp-answer-bank.merge_corrections` consumes.
- **Reason taxonomy** — `FACTUAL_ERROR`, `OUTDATED_SOURCE`, `TONE_OR_STYLE`, `MISSING_CONTEXT`, `CATEGORY_MISCLASSIFICATION`, `UNANSWERABLE_FROM_KB`, `POLICY_UPDATE`, `COMPLIANCE_NUANCE`. Tone-edits longer than 120 characters are auto-reclassified as `FACTUAL_ERROR` to prevent silent factual changes from being marked cosmetic.

### 3.7 `rfp-assemble`

Trigger phrases include *"assemble the RFP response"*, *"build the submission package"*, *"generate RFP deliverable"*, *"create analytics report"*, *"package the RFP for submission"*.

- **Purpose** — Take reviewed, gate-approved responses and produce a branded buyer-format submission (Word, Excel, PDF, or portal CSV), a cover letter, an analytics report, and a durable Record Set with full provenance.
- **Scripts** — `assemble_document.py` builds a manifest describing sections, ordering, and content blocks, and refuses to proceed if the provenance appendix row count does not equal the question count; `generate_analytics_report.py` computes match rate, tier distribution, and SME hours saved using only deterministic arithmetic; `package_submission.py` zips the artefacts and records SHA-256 hashes in the manifest.
- **The Record Set** — A self-contained zip containing the original RFP, extracted question bank, fit memo, drafted responses with provenance, gate audit trail, corrections log, buyer-format submission, cover letter, analytics report, shared audit log, and the manifest itself.
- **Final guardrail** — The skill **never** uploads to the buyer portal. The Ready-to-Submit card deep-links to the zip and the buyer's portal URL; the human deal lead performs the actual submission.

---

## 4. Workflow DAG and Data Flow

The swarm forms a directed acyclic graph with `rfp-answer-bank` acting as a substrate read by every other skill:

```
rfp-intake
  │ (task_list.json, rfp_metadata.json, classified.json)
  ▼
rfp-fit-assessment ◄── rfp-answer-bank (KB match stats)
  │ (fit_result.json + HUMAN_DECISION_LOGGED event required)
  ▼
rfp-respond ◄── rfp-answer-bank (per-question hybrid search)
  │ (responses.json with tier, confidence, source, flags)
  ▼
rfp-gates  (Security, Legal, Pricing — all three must Approve)
  │ (gate_verdict.json + PIPELINE_RESUMED event)
  ▼
rfp-review ◄── rfp-answer-bank (KB challenges, fresh-entry lookup)
  │ (responses_for_assembly.json, corrections.jsonl)
  │
  └─► rfp-answer-bank.merge_corrections   [closes the learning loop]
  ▼
rfp-assemble  (buyer-format deliverable, analytics, Record Set)
  │
  ▼
[ HUMAN SUBMITS to buyer portal ]
```

The graph is acyclic in execution order, but the answer-bank substrate makes it cyclic in *knowledge* flow: corrections captured by `rfp-review` become higher-tier matches the next time a similar question appears.

---

## 5. The Working-Directory Blackboard

Every persistent state in the swarm lives in either `working/` (transient, per-RFP) or `output/rfp-<rfp_id>/` (durable, shipped to the buyer or archived). No skill calls another skill directly; instead, each skill reads the JSON outputs of upstream skills and writes JSON for downstream consumers. This is the classic **blackboard architecture** from agent-systems research, instantiated as a flat file tree.

| File | Producer | Consumers | Lifecycle |
|---|---|---|---|
| `working/task_list.json` | `rfp-intake` | `rfp-fit-assessment`, `rfp-respond` | Immutable after intake |
| `working/rfp_metadata.json` | `rfp-intake` | All downstream | Immutable after intake |
| `working/fit_result.json` | `rfp-fit-assessment` | `rfp-assemble` (record set) | Read-only for analysis |
| `working/responses.json` | `rfp-respond` | `rfp-gates`, `rfp-review` | Append-only per question |
| `working/gate_verdict.json` | `rfp-gates` | `rfp-review`, `rfp-assemble` | Immutable after verdict |
| `working/corrections.jsonl` | `rfp-review` | `rfp-answer-bank.merge` | Append-only |
| `working/responses_for_assembly.json` | `rfp-review` | `rfp-assemble` | Immutable after review |
| `output/rfp-<id>/audit-log.xlsx` | All skills (via `append_audit.py`) | All skills (read) | Append-only audit trail |

The blackboard pattern decouples skills temporally and topologically: a future skill can be inserted between two existing ones without modifying either, provided it respects the JSON contract. It also makes every state inspectable. A user — or an auditor — can open the working directory at any point and see exactly what the swarm believes about the world.

---

## 6. Human-in-the-Loop Checkpoints

The swarm has four mandatory human checkpoints. None can be bypassed by the agent; each blocks the next skill until a corresponding audit event is written.

| Skill | Checkpoint | Decision | Blocker |
|---|---|---|---|
| `rfp-fit-assessment` | Go/No-Go memo review | Named decision owner signs | `HUMAN_DECISION_LOGGED` required |
| `rfp-gates` | Three parallel approvals | Security + Legal + Pricing | Pipeline pauses until all PASS |
| `rfp-review` | Reviewer queue triage | Approve, edit, or escalate | `review_status` field on each response |
| `rfp-assemble` | Pre-assembly + final submit | Deal lead confirms artefacts | Human uploads to portal — never automated |

These checkpoints are not advisory. They are encoded as Python script preconditions: `rfp-respond` will not start without `HUMAN_DECISION_LOGGED` in the audit log; `assemble_document.py` refuses to run if any response is missing `review_status`; `gate_status_tracker.py` emits a FAIL verdict if any of the three gates is missing or Rejected. **The human signal is structurally required, not just policy-recommended.**

---

## 7. Audit and Provenance

Every skill appends immutable events to a single shared workbook — `output/rfp-<rfp_id>/audit-log.xlsx` — using the shared `append_audit.py` script owned by `rfp-answer-bank`. The event catalogue is defined in `references/audit-log-schema.md` and includes events for intake, classification, fit assessment, drafting, gating, review, knowledge-base mutations, and assembly. Because the schema is owned by one skill and the writer is a single script, every event uses the same column order and timestamp format, which makes the workbook trivially queryable.

Provenance is enforced structurally. Every response in the final Record Set carries `response_id`, `question_id`, `source` (either `bank_entry:<KB-ID>` or `generated+reviewed`), `tier`, `reviewer`, `review_status`, and `last_updated`. The provenance appendix is embedded into the buyer-format deliverable: as an appendix and margin comments in Word, as extra columns in Excel, as a flattened section in PDF, and as a sidecar `manifest.json` in portal-CSV submissions. `assemble_document.py` refuses to run if the appendix row count does not equal the question count.

---

## 8. Confidence and Tier Propagation

The swarm uses a single confidence model with a single immutable rule: **no generated response may exceed 75 confidence, ever.** Only a human reviewer may promote a tier.

| Tier | Threshold | Treatment |
|---|---|---|
| HIGH | reranker ≥ 0.90 | Used verbatim from KB. Auto-approved if fresh (< 90 days) and non-sensitive. |
| MEDIUM | 0.75 – 0.89 | Lightly adapted within an allowed-edits list. Delta logged for audit. |
| LOW | < 0.75 | Generated by LLM, capped at 75 confidence, flagged for mandatory SME review. |
| GENERATED | no KB match | Always flagged. Always reviewed. Cannot be promoted by automation. |

Tier flows through the pipeline. `rfp-gates` reads tier but never promotes it. `rfp-review` can promote LOW → MEDIUM → HIGH after human edit, but only by appending a correction with reviewer signature. `rfp-assemble` preserves the original tier in the Record Set so an auditor can later distinguish KB-sourced answers from human-promoted ones.

---

## 9. AI Judgment vs Deterministic Computation

A defining characteristic of the swarm is the discipline with which it segregates LLM judgment from deterministic Python.

| Step | Mechanism | Notes |
|---|---|---|
| Intake parsing | Regex + heuristics | Pure Python; no LLM |
| Question classification | Taxonomy signals + LLM tie-break | Rule-based first; LLM only for ambiguous cases |
| Fit dimension scoring | Human input + rubric anchors | AI provides context; human assigns 0–5 scores |
| Memo generation | Template substitution | No free-form LLM; only `[PLACEHOLDER]` tokens |
| Answer-bank search | Hybrid BM25 + vector + reranker | Deterministic retrieval; tier thresholds in code |
| MEDIUM-tier adaptation | LLM within allowed-edits list | Bounded LLM; delta logged |
| LOW-tier generation | LLM synthesis | Capped at 75 confidence; flagged; preamble inserted |
| Gate prechecks | Cert + audit-date + clause matching | Deterministic comparison against authoritative lists |
| Gate decision | Human judgment + evidence pack | AI formats evidence; human decides |
| Review queue ranking | Six-tier rule-based sort | Deterministic; no LLM |
| Correction merge | Per-reason routing rules | Idempotent script; no LLM |
| Document assembly | Manifest-driven rendering | Built-in skills render bytes; no LLM in critical path |
| Analytics report | Arithmetic aggregation | Pure stdlib; no LLM |

**The pattern:** LLM judgment is reserved for retrieval-failure paths and natural-language adaptation. Everything else — routing, scoring, validation, document assembly, audit logging — is deterministic Python. This makes the swarm both faster and more defensible. A reviewer challenging an answer can trace every score, every routing decision, and every formatting choice to a specific line in a specific script.

---

## 10. How the Swarm Integrates with Cowork's Agentic Loop

Cowork's agent loop is a tool-using LLM that selects skills based on user intent and trigger phrases declared in YAML frontmatter. The RFP swarm exploits this in three ways.

### 10.1 Trigger overlap is intentional

Several skills declare overlapping trigger phrases (*"run RFP"*, *"RFP help"*, *"send for approval"*). The agent disambiguates by reading the operational instructions and matching the current state of `working/` files. For example, *"send for approval"* matches both `rfp-gates` and `rfp-review`; the agent inspects whether `responses.json` already exists with confidence tiers (gates) or whether `gate_verdict.json` exists with FAILs (review).

### 10.2 Hand-off via written state, not callback

Skills do not invoke each other. When `rfp-intake` finishes, it writes `task_list.json` and emits a `TASK_LIST_CREATED` audit event with a suggested next-skill hint. The agent reads the hint and the `working/` contents, decides `rfp-fit-assessment` is appropriate, and loads its `SKILL.md`. This is RAG — retrieval-augmented generation — *at the orchestration layer*: the agent retrieves the next skill from the workspace state.

### 10.3 Built-in skills as primitives

Each RFP skill leverages built-in Cowork skills as primitives: `docx` for Word output, `xlsx` for Excel workbooks, `pdf` for flattened deliverables, `render-ui` for Adaptive Cards, `deep-research` for novel question synthesis, Outlook MCP for approval-request emails, Teams MCP for SME hand-offs, SharePoint/OneDrive MCP for file storage, and Enterprise Search for buyer history. The swarm composes the orchestration layer; the primitives handle file format, transport, and retrieval.

---

## 11. Architectural Patterns

Six recurring patterns emerge from the swarm. We believe these generalise to any agentic workflow combining LLM reasoning with deterministic processing and human accountability.

**Pattern 1 — Skill-as-Orchestration-Layer.** Each skill is an *orchestrator*, not a tool. It composes deterministic scripts, on-demand reference lookups, static templates, and LLM judgment into an end-to-end phase of the workflow. The agent does not need to know how parsing works — it only needs to know that `rfp-intake` handles *"a new RFP came in"* and writes `task_list.json`.

**Pattern 2 — Working-Directory Blackboard.** Skills communicate through a flat file tree, never through direct invocation. State is inspectable. Skills can be inserted, removed, or replaced without modifying their neighbours, provided they respect the JSON contract.

**Pattern 3 — Retrieval-First Generation.** Search the curated knowledge base before invoking any LLM. Use HIGH-tier matches verbatim. Adapt MEDIUM matches within bounded edit rules. Generate only when retrieval fails — and flag everything generated.

**Pattern 4 — Confidence-Tier Capping.** Generated content is structurally capped at MEDIUM confidence. Only human reviewers can promote tier. The cap propagates through gates, review, and assembly without any agent able to override it.

**Pattern 5 — Non-Overridable Human Gates.** Critical decisions (Go/No-Go, Security, Legal, Pricing) are encoded as script preconditions. There is no force flag. Deadline pressure does not unlock gates. The agent cannot bypass the human signal because the next script will not start without the corresponding audit event.

**Pattern 6 — Append-Only Audit and Embedded Provenance.** All skills write to a single shared audit log via a single shared script. Provenance is embedded into the final deliverable per format (appendix, columns, footer, sidecar). Assembly refuses to run if the provenance row count does not match the question count.

---

## 12. Limitations and Future Work

- **External KB substrate.** The hybrid search index is external to the skill bundle. The swarm assumes the index exists and is populated; bootstrapping a new tenant requires a Loopio export or equivalent.
- **Tuned thresholds.** Tier thresholds (0.90 for HIGH, 0.75 for MEDIUM) are tuned for one reranker model; a different reranker would require recalibration. The thresholds live in `references/confidence-tier-rules.md`, which is documented but not auto-tuned.
- **Approval routing assumptions.** The swarm assumes the org has Security Lead, Legal Counsel, and Account Exec roles staffed and reachable via Adaptive Cards. Smaller organisations may need to collapse roles.
- **Manual final submission.** Final portal submission remains manual. Automating this would require buyer-portal API integrations (Ariba, Coupa, Jaggaer) outside the current scope.
- **English-only.** The swarm does not currently support multi-language RFPs. Trigger phrases, taxonomy signals, and the tone guide are English-only.

---

## 13. Conclusion

The RFP Skill Swarm is a working example of a sophisticated agentic system built entirely on Microsoft 365 Copilot Cowork's skill model. It combines 22 standard-library Python scripts, 26 reference documents, 10 templates, and seven `SKILL.md` manifests into a pipeline that takes an RFP from inbox to submission package. The architecture is defensible: every answer is sourced or flagged, every decision is logged, every gate requires a named human approver, and every deliverable carries embedded provenance.

Beyond RFP response, the swarm illustrates a broader principle: **LLMs are most useful at the *seams* of deterministic workflows, not as the workflow itself.** The agent's job is to orchestrate — to recognise intent, select the right skill, and read the workspace state. The skill's job is to compose deterministic computation, structured retrieval, and bounded LLM judgment into a defensible outcome. When this division of labour is enforced by script preconditions and append-only audit logs, the result is automation that organisations can trust with commercial bids.

---

## Appendix A — Script Inventory

| Skill | Script | Purpose |
|---|---|---|
| `rfp-intake` | `parse_rfp.py` | Extract questions and metadata |
| `rfp-intake` | `classify_questions.py` | Assign categories from taxonomy |
| `rfp-intake` | `build_task_list.py` | Deduplicate and merge |
| `rfp-fit-assessment` | `kb_match_estimator.py` | Estimate KB coverage |
| `rfp-fit-assessment` | `compute_fit_score.py` | Weighted scorecard |
| `rfp-fit-assessment` | `generate_go_no_go_memo.py` | Template substitution |
| `rfp-answer-bank` | `search_bank.py` | Hybrid retrieval |
| `rfp-answer-bank` | `add_entry.py` | Validate + version new entries |
| `rfp-answer-bank` | `sync_loopio_export.py` | Diff + import Loopio CSV |
| `rfp-answer-bank` | `merge_corrections.py` | Idempotent correction merge |
| `rfp-answer-bank` | `append_audit.py` | Sole audit-log writer |
| `rfp-answer-bank` | `render_audit_dashboard.py` | Audit timeline export |
| `rfp-respond` | `route_to_specialists.py` | Team routing |
| `rfp-respond` | `confidence_scorer.py` | Tier capping |
| `rfp-respond` | `draft_responses.py` | Retrieval-first orchestrator |
| `rfp-gates` | `run_gates.py` | Automated prechecks |
| `rfp-gates` | `send_gate_approval.py` | Adaptive Card payload |
| `rfp-gates` | `gate_status_tracker.py` | Verdict aggregation |
| `rfp-review` | `build_review_queue.py` | Six-tier prioritisation |
| `rfp-review` | `log_correction.py` | Append correction with reason enum |
| `rfp-review` | `export_corrections.py` | Roll up for KB merge |
| `rfp-assemble` | `assemble_document.py` | Manifest builder |
| `rfp-assemble` | `generate_analytics_report.py` | Arithmetic aggregation |
| `rfp-assemble` | `package_submission.py` | Zip + SHA-256 + manifest |

All 22 scripts above pass syntax compilation, expose `argparse` CLIs, and use only the Python standard library. They are runnable inside the Cowork sandbox without any installation step.

---

> **Note on this document.** This research paper was authored alongside the working skill packages and reflects an analysis of the swarm as it stood on 23 April 2026. As the skills evolve, this paper will be revised. See [README.md](README.md) for the curated overview and [`../DISCLAIMER.md`](../DISCLAIMER.md) for repo-wide caveats.

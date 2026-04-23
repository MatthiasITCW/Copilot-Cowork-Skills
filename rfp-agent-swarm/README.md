# RFP Agent Swarm — An Art-of-the-Possible

*A research exploration of how Copilot Cowork custom skills can be composed into a hierarchical, human-in-the-loop agent swarm that takes an inbound Request for Proposal from first ingestion through to an approved, branded submission package.*

> **This is a research document.** It describes one possible architecture, not a shipped Microsoft product. The skills linked here are working artefacts built to explore the pattern — not a production-ready system. See the [Disclaimers](#disclaimers) before adopting any of it.

> 📄 **Full architectural study:** see [RESEARCH-PAPER.md](RESEARCH-PAPER.md) for the long-form analysis (script audit, blackboard model, confidence-tier propagation, the six recurring patterns, and the AI-vs-deterministic decomposition).

---

## At a Glance

| | |
|---|---|
| **Skill packages** | 7 `SKILL.md` manifests |
| **Python scripts** | 22 (100 % stdlib, 100 % `argparse` CLIs, 100 % syntax-clean) |
| **Reference docs** | 26 on-demand Markdown lookup tables |
| **Static assets** | 10 verbatim templates |
| **External dependencies** | **Zero** — runs in any Python 3.8+ sandbox |
| **Hard human gates** | 4 (Go/No-Go, Security, Legal, Pricing) — non-overridable |
| **Generation confidence cap** | 75 (only humans can promote tier) |

---

## The Problem

Responding to a Request for Proposal (RFP), RFI, RFQ, tender, or enterprise security questionnaire is one of the most expensive forms of knowledge work inside a typical B2B organisation:

- A single large RFP can contain 300+ questions spanning Security, Technical, Commercial, Legal, and Company domains.
- Most answers already exist somewhere — in a prior response, a SharePoint policy doc, a Loopio-style knowledge base, or in the head of a subject-matter expert.
- The hard parts are: finding the right prior answer, adapting it, getting it reviewed by the right person, passing the mandatory internal gates (security, legal, pricing), and assembling the final deliverable in the buyer's required format.
- Human reviewers are the bottleneck, and every correction they make is information that rarely flows back into the knowledge base.

RFPs are an ideal test case for an agent-swarm pattern: the work is large, decomposable, retrieval-heavy, and deeply dependent on structured human approval.

---

## The Hypothesis

> A *small* set of cooperating, narrowly-scoped Cowork skills — each one doing a single step well, each one handing structured JSON to the next — can take an inbound RFP from email attachment to reviewed, gate-approved submission package, with every answer traceable to a knowledge-base source or a named human approver, and with every reviewer correction captured to improve the next run.

This is not about replacing the bid team. It is about **amplifying** them: automating the mechanical work (parsing, classifying, retrieving, first-draft writing, assembling) so that human attention is spent where it actually matters — on the 20–30% of answers that are novel, risky, or commercially sensitive.

---

## The Pattern — Seven Skills in a Pipeline

The swarm is a deliberately linear pipeline with one shared substrate (the answer bank) that every stage reads from and some stages write to.

```
              ┌──────────────────────┐
              │   rfp-answer-bank    │   ← shared substrate
              │  (KB + audit log)    │     (read by every step)
              └──────────┬───────────┘
                         │
 ┌──────────┐   ┌──────────────────┐   ┌──────────────┐   ┌──────────────┐
 │ rfp-     │──▶│ rfp-fit-         │──▶│ rfp-respond  │──▶│ rfp-gates    │
 │ intake   │   │ assessment       │   │              │   │              │
 └──────────┘   └──────────────────┘   └──────────────┘   └──────┬───────┘
                                                                 │
                                                                 ▼
                                                       ┌──────────────────┐
                                                       │  rfp-review      │
                                                       └─────────┬────────┘
                                                                 │
                                                                 ▼
                                                       ┌──────────────────┐
                                                       │  rfp-assemble    │
                                                       └──────────────────┘
```


### The Seven Skills

| # | Skill | Role in the pipeline |
|---|---|---|
| 0 | [`rfp-answer-bank`](skills/rfp-answer-bank/) | **Shared substrate.** Owns the retrievable knowledge base, the canonical audit-log schema, and the sole writer to the audit log. Every other skill reads from it; `rfp-review` feeds corrections back into it. |
| 1 | [`rfp-intake`](skills/rfp-intake/) | Parse the inbound document (PDF/DOCX/XLSX), extract every question, classify by team (Security / Technical / Commercial / Company / General), detect mandatory vs optional, and produce a structured task list plus an intake card with buyer metadata. |
| 2 | [`rfp-fit-assessment`](skills/rfp-fit-assessment/) | Run a weighted Go/No-Go scorecard across seven dimensions (KB match rate, technical fit, commercial fit, competitive position, strategic alignment, resource availability, deadline feasibility) and produce an advisory memo. **The human always makes the final call.** |
| 3 | [`rfp-respond`](skills/rfp-respond/) | Retrieval-first drafting. Search the answer bank first; generate only if no acceptable match exists. Every answer gets a confidence tier (HIGH / MEDIUM / LOW), a provenance reference, and a reviewer flag where warranted. Routes questions to Security / Technical / Commercial processing in parallel. |
| 4 | [`rfp-gates`](skills/rfp-gates/) | Three non-negotiable approval gates — Security Completeness, Legal Review, Pricing Approval. Prepares evidence, dispatches Teams adaptive-card approval requests to named approvers, tracks responses, and blocks progression until all three return Approved. |
| 5 | [`rfp-review`](skills/rfp-review/) | Triaged human-review queue. Surfaces only flagged / low-confidence items for reviewer attention, captures every correction with a structured reason code, and exports the corrections payload that closes the learning loop back into the answer bank. |
| 6 | [`rfp-assemble`](skills/rfp-assemble/) | Produce the final deliverable in the buyer's required format (Word narrative, Excel questionnaire, flattened PDF, or portal CSV/JSON for Ariba / Coupa / Jaggaer). Apply branding, attach cover letter, generate an analytics report (match rate, confidence distribution, gate outcomes, effort) with full provenance. |

---

## Design Principles

These are the ideas the swarm is built around. They are deliberately stated up front because they shape every skill boundary.

1. **Retrieval over generation.** For every question, the answer bank is searched first. Generation is a last resort, capped at medium confidence, and never ships without human review.
2. **Confidence tiering is mandatory.** Every drafted answer carries HIGH / MEDIUM / LOW and provenance. Tiers determine what a human must look at.
3. **Transparency over automation.** Every HIGH-confidence auto-answer is logged; every LOW-confidence or generated answer is seen by a human. The pipeline is designed for auditability, not speed.
4. **Gates are blocking and human-signed.** `rfp-gates` will not allow assembly until a named human approves each of Security, Legal, and Pricing. The skill orchestrates the approvals; it does not make them.
5. **Corrections close the loop.** Every reviewer correction is logged with a structured reason code. Those corrections are the raw material that improves the next run's KB match rate.
6. **One audit trail to rule them all.** All seven skills write to a single `audit-log.xlsx` via one shared script owned by `rfp-answer-bank`. There is exactly one canonical Event Type Catalogue.
7. **Narrow skills, explicit contracts.** Each skill has a single job and a documented upstream/downstream contract. No skill re-drafts answers once `rfp-respond` has written them; no skill touches the KB without going through `rfp-answer-bank`.
8. **The human signs the bid.** This stack produces an excellent *draft*. It never submits. A named deal lead always does the final click.

---

## Six Recurring Patterns

A detailed audit of the swarm (see [RESEARCH-PAPER.md §11](RESEARCH-PAPER.md#11-architectural-patterns)) surfaces six patterns we believe generalise to *any* agentic workflow that combines LLM reasoning with deterministic processing and human accountability.

| # | Pattern | What it means in practice |
|---|---|---|
| 1 | **Skill-as-Orchestration-Layer** | Each skill is an *orchestrator*, not a tool. It composes deterministic scripts, on-demand reference lookups, static templates, and LLM judgment into one end-to-end phase. |
| 2 | **Working-Directory Blackboard** | Skills communicate through a flat file tree (`working/`, `output/rfp-<id>/`), never through direct invocation. State is inspectable; skills can be inserted or replaced without touching neighbours. |
| 3 | **Retrieval-First Generation** | Search the curated KB before invoking any LLM. Use HIGH-tier matches verbatim, adapt MEDIUM matches within bounded edit rules, generate only when retrieval fails — and flag everything generated. |
| 4 | **Confidence-Tier Capping** | Generated content is structurally capped at MEDIUM confidence (75). Only human reviewers can promote tier. The cap propagates through gates, review, and assembly with no agent able to override it. |
| 5 | **Non-Overridable Human Gates** | Critical decisions (Go/No-Go, Security, Legal, Pricing) are encoded as Python script preconditions. No force flag, no bypass token. The next script will not start without the corresponding audit event. |
| 6 | **Append-Only Audit + Embedded Provenance** | All skills write to one shared audit log via one shared script. Provenance is embedded in every deliverable (Word appendix, Excel columns, PDF footer, CSV sidecar). Assembly refuses to run if the appendix row count ≠ question count. |

---

## The AI / Deterministic Split

A defining characteristic of the swarm is the discipline with which it segregates LLM judgment from deterministic Python. **LLM judgment is reserved for retrieval-failure paths and natural-language adaptation. Everything else is code.** The full table is in [RESEARCH-PAPER.md §9](RESEARCH-PAPER.md#9-ai-judgment-vs-deterministic-computation); the headline split is:

| Use deterministic Python for… | Use LLM judgment for… |
|---|---|
| Question parsing, classification, deduplication | Tie-breaking ambiguous classifications |
| Weighted scorecard arithmetic | Surfacing context to help a human assign 0–5 scores |
| Memo / template generation (`[PLACEHOLDER]` substitution) | Adapting MEDIUM-tier KB answers within a bounded edit list |
| Hybrid BM25 + vector + reranker retrieval | Generating LOW-tier answers when retrieval fails |
| Tier capping, routing, queue ranking | Drafting cover-letter prose where bounded |
| Document assembly, packaging, SHA-256 manifests | (none — assembly is 100 % deterministic) |
| Append-only audit logging | (none — auditing is 100 % deterministic) |

The payoff: a reviewer challenging an answer can trace every score, every routing decision, and every formatting choice to a specific line in a specific script.

---

## Architecture Overview

At a coarse grain the swarm follows a **Refiner / Reviewer** pattern at each team-specialised stage, with a shared retrieval substrate and a single **Lead Orchestrator** role (realised by the user prompting in sequence, or by an orchestration layer above Cowork):

- **Lead Orchestrator** — decomposes the RFP via `rfp-intake`, runs `rfp-fit-assessment`, and at the end runs `rfp-assemble` to synthesise the final package.
- **Domain refiners** — `rfp-respond` dispatches questions to Security / Technical / Commercial specialist pathways, each of which drafts against the answer bank.
- **Reviewers** — `rfp-gates` and `rfp-review` play the Reviewer role: gates enforce non-negotiable compliance, review captures the structured correction signal.
- **Shared memory** — `rfp-answer-bank` is the long-term memory; the per-RFP `output/rfp-<id>/audit-log.xlsx` is the short-term memory.

### Technology Shape (reference only)

The skills themselves are implementation-agnostic Markdown + Python + static assets. A notional backing stack might look like:

- **Orchestration / UI**: Microsoft 365 Copilot Cowork (primary), optionally extended via Copilot Studio or a lightweight orchestrator for A2A (agent-to-agent) messaging.
- **Retrieval substrate**: A vector + keyword hybrid index over a curated answer bank (Azure AI Search or equivalent), with Loopio as an optional system-of-record for approved Q&A.
- **Approvals**: Teams Adaptive Cards for gate approvals.
- **Deliverables**: Word / Excel / PDF via the built-in Cowork document skills.

The skill packages in this repo make no assumption about any specific vendor for the substrate — they define the *contracts* (schemas, confidence tiers, audit events) and leave the implementation to the adopter.

---

## Quick Start

1. **Read** the `SKILL.md` for each of the seven skills under [`skills/`](skills/). They are the canonical specification; everything else on this page is commentary.
2. **Install** the skills into your Cowork personal skills library (via OneDrive). Start with `rfp-answer-bank` because every other skill depends on it.
3. **Try it on a throwaway RFP.** Give Cowork a sample tender PDF and say *"parse this RFP"*. That triggers `rfp-intake`. Then walk the pipeline step by step.
4. **Inspect the audit log.** The most informative artefact is `output/rfp-<id>/audit-log.xlsx` — every decision, every gate, every correction is there.

---

## Honest Limits

This is research. Things it does **not** do yet:

- **No autonomous orchestration.** Today a human (or a thin Copilot Studio topic) drives the pipeline step-to-step. True agent-to-agent chaining with backpressure, retries, and branch-on-failure is future work.
- **No real-time gate dispatch.** The gate skill describes the adaptive-card pattern; wiring it to a live Teams channel requires organisation-specific integration.
- **No production hardening of the answer bank.** The schema is robust; the ingestion pipeline for a large historical Loopio export is sketched, not battle-tested.
- **Limited evaluation harness.** There is no published benchmark set for RFP answering. Confidence tiers are heuristic, not calibrated.
- **Format coverage.** The `rfp-assemble` skill prioritises Word and Excel output. Portal-specific CSV/JSON for every procurement system (Ariba, Coupa, Jaggaer, SAP SLP, etc.) needs per-portal mapping work.

---

## Disclaimers

- **Research artefact.** This pattern and the skills under [`skills/`](skills/) are exploratory. They have **not** been formally evaluated, penetration-tested, or privacy-reviewed for production use.
- **Not a Microsoft product.** Not endorsed, supported, or warranted by Microsoft. Official Copilot Cowork guidance lives at [Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/) and supersedes anything here.
- **No customer data.** All company names (`Contoso`), email domains (`contoso.com`), sample answers, and placeholder URLs are generic. No real customer, contract, pricing, or confidential information is represented.
- **Regulated content.** RFPs routinely contain security, legal, and pricing claims that carry contractual weight. Do not ship any output of this swarm without appropriate human review by qualified owners (CISO or delegate for security; Legal for legal; Deal Desk / CFO delegate for pricing).
- **Model risk.** Retrieval-first drafting dramatically reduces hallucination but does not eliminate it. Any generated (non-KB) answer must be reviewed before submission.
- **AI transparency.** If you use this pattern to produce customer-facing bid responses, consider disclosing the use of AI assistance where your customer, jurisdiction, or bid rules require it.
- **Data residency and licensing.** Running these skills routes data through Microsoft 365 Copilot Cowork. Confirm your tenant's data-residency, retention, and licensing posture before processing any real RFP.

---

## Related Reading

- [RESEARCH-PAPER.md](RESEARCH-PAPER.md) — the full long-form architectural study (script audit, blackboard model, AI-vs-deterministic split, six patterns, script inventory).
- [Microsoft 365 Copilot Cowork — Use custom skills](https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/use-cowork#create-custom-skills)
- [`../skill-factory/`](../skill-factory/) — the meta-skill used to scaffold most of the packages under [`skills/`](skills/).
- [`../README.md`](../README.md) — repo-level overview and roadmap.

---

*Last updated: April 2026. This page is a living document and will be revised as the pattern evolves.*

# Team Specialist Guides

Per-team operating manual for the parallel drafting teams invoked by `rfp-respond`. Used by `scripts/route_to_specialists.py` to assign questions and by the downstream team agents that actually draft.

Each team has a **lead** that coordinates and **specialist agents** that execute. All teams write to the same `working/responses.json`, keyed by `question_id`, with atomic writes to avoid conflicts.

## 1. Security Team

**Lead:** Security Lead
**Agents:** Security Questionnaire agent, Compliance Analyst
**Primary queue signal:** tags include `security`, `compliance`, `privacy`, `audit`, `pentest`, `encryption`, `vulnerability`.

### 1.1 Security Questionnaire Agent

Handles standardised questionnaires. Recognised formats and their quirks:

| Format | Notes |
|---|---|
| SIG (Shared Assessments) | Core + Lite variants; questions reference SCF controls; answers expected as Yes/No/N/A with supporting narrative. Bank entries are tagged `sig-core` / `sig-lite`. |
| CAIQ (Cloud Security Alliance) | Maps to CCM domains; answers expected as Yes/No/NA with reference. Preserve the CCM question ID in the response row. |
| VSA (Vendor Security Alliance) | Core, Full, and Plus. Expect free-text with evidence links. |
| HECVAT | Higher-ed focused; includes institution-specific supplement. Preserve HECVAT question code in `metadata.hecvat_code`. |

Rules:

- Never convert a "Partial" bank answer into "Yes". If the source says partial, the response says partial.
- Evidence links in bank entries must be preserved verbatim. Do not substitute a different report URL even if one looks newer.
- For format-specific yes/no fields, the narrative body still goes in `response_text`; the yes/no goes in `metadata.answer_code`.

### 1.2 Compliance Analyst

Owns framework-specific questions: SOC 2, ISO 27001, GDPR, HIPAA, PCI-DSS, FedRAMP (where applicable), and regional equivalents (UK DPA, LGPD).

Rules:

- **Never invent a certification.** If the bank does not contain an approved statement that we hold a certification, the response is LOW and flagged.
- **Never invent an audit date.** If the buyer asks "when was your last SOC 2 audit?", the answer must come from a bank entry that explicitly records the date.
- Audit timelines referenced in the response must match the timeline in the source bank entry within a 30-day tolerance; beyond that, escalate for fresh verification.
- GDPR questions that touch cross-border transfers require the current SCC annex version — keep the annex reference on the bank entry in sync.

### 1.3 Security handoffs

- Security question with an integration angle (e.g. "how is SSO secured") → Security primary, Technical consulted.
- Security question embedded in an MSA/DPA clause → Security primary, Commercial (Legal Review) consulted.

## 2. Technical Team

**Lead:** Technical Lead
**Agents:** Product Capabilities, Integration Specialist
**Primary queue signal:** tags include `feature`, `architecture`, `deployment`, `sla`, `api`, `sso`, `scim`, `migration`, `performance`.

### 2.1 Product Capabilities

Handles feature, architecture, deployment-model, and SLA questions.

Rules:

- Specificity matters. Replace "we support this" with named components (e.g. "the Ingest API, v2, with 10k req/min rate limit").
- SLA figures must come from the contractual SLA entry in the bank. Never quote a figure from a marketing page.
- Deployment-model questions (cloud, single-tenant, private, on-prem): use the up-to-date deployment matrix in `BANK-DEPLOY-*`. Do not mix-and-match features between models.
- **No overpromising.** If the bank entry says "roadmap", the response says "roadmap, currently scheduled for [source-stated quarter], subject to change". If there is no roadmap entry, flag LOW.

### 2.2 Integration Specialist

Handles APIs, SSO/SCIM, data migration, webhooks, event streams, and third-party connector questions.

Rules:

- API questions: include the latest supported version and the deprecation policy from the bank.
- SSO answers must list supported IdPs tested within the last 12 months (bank entry `last_approved_date` <= 12 months old). Older lists are MEDIUM with a delta noting the scope.
- Data migration timeframes: only quote from a sized, documented customer example in the bank. Do not extrapolate.
- Custom integrations: default answer is "available via professional services, scope and pricing to be agreed" — never quote a figure.

### 2.3 Technical handoffs

- Technical question about a compliance-sensitive flow (e.g. "how does your backup system handle GDPR deletion requests?") → Technical primary, Security consulted.
- Technical question tied to a contractual SLA → Technical primary, Commercial consulted.

## 3. Commercial Team

**Lead:** Commercial Lead
**Agents:** Company Overview / Case Studies, Pricing Specialist, Legal Review Agent
**Primary queue signal:** tags include `company`, `reference`, `case-study`, `pricing`, `commercial`, `msa`, `dpa`, `legal`, `terms`.

### 3.1 Company Overview & Case Studies

Handles "tell us about your company" and reference questions.

Rules:

- Customer names must come from the approved reference list (`BANK-REF-*`), which records the permission scope (public, under-NDA-named, anonymised-only).
- Metrics (ARR, headcount, customer count) come from the approved boilerplate entry with a clear "as of" date. Update quarterly.
- Never use a reference that has an `expires_on` date in the past.

### 3.2 Pricing Specialist

Structures pricing responses from authorised inputs. **Does not generate figures.**

Rules:

- Input required: `working/pricing_inputs.json`, signed off by Commercial Lead.
- If input is missing, response is `NEEDS_AUTHORISED_INPUT` and the question is held (not LOW-generated).
- Structures include: unit pricing, tiered pricing, volume discounts, professional services day rates, implementation one-off, renewal uplift caps.
- All figures in the response must trace, line-for-line, to `pricing_inputs.json`. `rfp-gates` verifies this.
- Currency, billing frequency, and price-hold period are required fields on every pricing row.

### 3.3 Legal Review Agent

Applies the legal playbook (see `legal-review` skill) to contractual questions and redline requests.

Rules:

- Every legal response carries `flags: ["HUMAN_APPROVAL_REQUIRED"]`. No exceptions.
- The agent **flags** non-standard clauses; it does not sign them off.
- Position papers from the playbook are reused verbatim (tier HIGH) where the buyer's wording matches. Adaptations (tier MEDIUM) require the counsel reviewer to confirm.
- Questions asking for indemnity caps, liability limits, or governing-law changes are always held for counsel regardless of tier.

### 3.4 Commercial handoffs

- DPA / cross-border data questions → Commercial primary, Security consulted.
- SLA clauses in MSA → Commercial primary, Technical consulted.
- Pricing + security-scope question ("price per endpoint scanned") → Commercial primary, Security consulted.

## 4. Multi-Team Questions: PRIMARY vs CONSULTED

Any question tagged for more than one team is resolved by `route_to_specialists.py` using this table:

| Tag combination | PRIMARY | CONSULTED |
|---|---|---|
| security + technical | security | technical |
| security + commercial | commercial | security |
| technical + commercial | commercial | technical |
| security + technical + commercial | security | technical, commercial |
| legal + anything | commercial (Legal Review) | others |
| pricing + anything | commercial (Pricing) | others |

Rules for consulted teams:

- PRIMARY owns the row in `responses.json`.
- CONSULTED teams contribute via `metadata.consulted_notes[]` — short notes appended to the row, not full paragraphs.
- CONSULTED teams do **not** write to the row directly; PRIMARY merges notes.

## 5. Load Balancing

`route_to_specialists.py` emits an estimated effort per team based on question count and question length. When one team's load exceeds 2x another's, the manifest includes an `imbalance_warning` so operators can pre-stage SMEs. This skill does not rebalance by moving questions — tags are authoritative.

## 6. Quick-Reference Rules Table

| Rule | Team | Teeth |
|---|---|---|
| Never fabricate a cert | Security | Cap 75 + flag |
| Never quote a marketing SLA | Technical | `rfp-gates` cross-checks contractual SLA bank entry |
| Never generate pricing | Commercial | Hold question until inputs provided |
| Every legal response needs human approval | Commercial | Flag is mandatory |
| Customer names must be on approved reference list | Commercial | Enforced by bank tag |
| Roadmap items always say "subject to change" | Technical | Enforced by tone guide |

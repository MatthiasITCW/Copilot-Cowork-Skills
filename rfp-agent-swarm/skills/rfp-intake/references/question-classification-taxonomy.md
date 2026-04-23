# RFP Question Classification Taxonomy

This reference defines the five categories every incoming RFP question is
sorted into, the keyword and pattern signals that drive classification, the
mapping from category to owner team, and the patterns used to flag a question
as mandatory or optional.

The taxonomy is consumed by [../scripts/classify_questions.py](../scripts/classify_questions.py).
Signal lists are deliberately short and illustrative, not exhaustive — they
are expected to be tuned as the swarm learns from human corrections captured
by rfp-review.

## Categories at a glance

| Category | Code | Owner team | Typical question count per RFP |
|----------|------|------------|-------------------------------|
| Security | SEC | Security Engineering | 40-120 |
| Technical | TEC | Solution Architecture | 20-80 |
| Commercial | COM | Commercial Desk | 10-30 |
| Company / Corporate | COR | Corporate Marketing | 5-20 |
| General / Operational | GEN | Bid Manager | 5-15 |

## Security (SEC)

Controls, certifications, data protection, incident response, privacy.

| Signal type | Examples |
|-------------|----------|
| Certifications | SOC 2, SOC2, ISO 27001, ISO 27017, ISO 27018, HIPAA, PCI DSS, FedRAMP, CSA STAR, Cyber Essentials |
| Cryptography | encryption at rest, encryption in transit, TLS 1.2, AES-256, key management, HSM, BYOK |
| Testing | penetration test, pen test, vulnerability scan, SAST, DAST, bug bounty, red team |
| Access controls | RBAC, least privilege, MFA, multi-factor, privileged access, PAM |
| Operations | SIEM, SOC, 24x7 monitoring, incident response, breach notification, RTO, RPO |
| Privacy | GDPR, CCPA, data residency, data subject rights, DPA, sub-processor |
| Frameworks | NIST 800-53, CIS Controls, CSA CCM, CAIQ, SIG, SIG Lite, HECVAT, VSA |
| Lifecycle | secure SDLC, SDL, code review, dependency scanning, SBOM |

Primary vs secondary: a question that asks about "API authentication" hits
both SEC (authentication) and TEC (API). Primary = SEC when the emphasis is
on the control; Primary = TEC when the emphasis is on the integration
pattern. The classifier uses signal density to decide.

## Technical (TEC)

Architecture, integration, performance, deployment, roadmap.

| Signal type | Examples |
|-------------|----------|
| Architecture | multi-tenant, single-tenant, microservices, event-driven, monolith, reference architecture |
| Integration | API, REST, GraphQL, webhook, SSO, SAML, OIDC, OAuth2, SCIM, LDAP |
| Deployment | cloud, on-prem, hybrid, private cloud, air-gapped, region, availability zone |
| Performance | latency, throughput, TPS, concurrent users, load test, benchmark |
| Availability | SLA, uptime, 99.9, 99.95, 99.99, failover, DR, disaster recovery |
| Data | data model, schema, export, import, ETL, streaming, retention |
| Roadmap | feature roadmap, future release, GA, beta, deprecation |
| Standards | OpenAPI, Swagger, ISO 20000, ITIL, CMMI |

## Commercial (COM)

Pricing, contract, commercial terms. Note: this skill only tags and routes
these; it never generates answers.

| Signal type | Examples |
|-------------|----------|
| Pricing model | per user, per seat, consumption, tiered, flat fee, enterprise license, ELA |
| Discounts | volume discount, multi-year discount, ramp, co-term |
| Payment | payment terms, net 30, net 60, invoicing cadence, billing |
| Contract | MSA, SOW, order form, term length, auto-renewal, termination for convenience |
| Performance credits | SLA credits, service credits, liquidated damages |
| Total cost | TCO, 3-year TCO, 5-year TCO, implementation cost, professional services |
| Legal adjacency | indemnification, liability cap, warranty (tag but do not answer) |

## Company / Corporate (COR)

Firmographic, reputational, references, sustainability.

| Signal type | Examples |
|-------------|----------|
| History | year founded, headquarters, ownership, parent company |
| Scale | number of employees, revenue, customer count, countries served |
| Stability | financial stability, Dun & Bradstreet, credit rating, audited financials |
| References | customer references, case studies, logos, analogous clients |
| Analyst | Gartner Magic Quadrant, Forrester Wave, IDC MarketScape |
| ESG / DE&I | diversity, equity, inclusion, sustainability, carbon, net zero, modern slavery |
| Insurance | cyber insurance, professional liability, general liability, aggregate limit |

## General / Operational (GEN)

Process, format, logistics. The bid manager owns these.

| Signal type | Examples |
|-------------|----------|
| Submission | submission format, submission portal, file format, page limit, font size |
| Schedule | Q&A deadline, clarification window, oral presentation, site visit |
| Contact | point of contact, single point of contact, SPOC, procurement contact |
| Template | proposal template, required sections, cover letter, executive summary |
| Language | response language, English only, dual language |
| Attachments | mandatory attachments, exhibits, appendices, redlines |

## Mandatory vs optional patterns

| Flag | Signal patterns |
|------|-----------------|
| Mandatory | must, shall, is required, is mandatory, required to, at minimum, no later than, non-negotiable, "(M)", "[Required]", "*" leading marker |
| Optional | may, might, optional, nice to have, preferred but not required, if available, "(O)", "[Optional]" |

Tie-breaking rules:

1. If a sentence contains both a mandatory and optional marker, mandatory wins.
2. If no marker is present, default to mandatory. Bias is toward over-answering.
3. A question listed under a "Mandatory Requirements" heading inherits the
   mandatory flag even if the sentence itself is neutral.
4. Security questionnaire templates (SIG, CAIQ, HECVAT) are all-mandatory by
   convention unless a column explicitly says otherwise.

## Edge-case guidance

| Situation | Handling |
|-----------|----------|
| Question spans Security and Technical | Primary = category with higher signal density; secondary = the other |
| Multi-part question ("a) ... b) ... c) ...") | Split into sub-questions with IDs Q-0042a, Q-0042b, Q-0042c; each classified independently |
| Question references an exhibit ("see Exhibit C") | Tag `evidence_required=true`; keep in primary category |
| Yes/No checkbox question | Still classified normally; word_limit_hint = 25 |
| Question with embedded table to be filled | Each table row becomes its own sub-question |
| Legal redline request | Tag COM with `legal_review=true`; explicit note that legal sign-off is human-only |
| Pricing table to complete | Tag COM with `pricing=true`; flagged so rfp-respond does NOT draft a number |
| Certification claim ("are you ISO 27001 certified?") | SEC with `credential_check=true`; Security Engineering must confirm from the cert register, never fabricated |
| Question in a language other than English | Flag `translation_required=true`; keep original text verbatim in `text`, add `text_en` after human translation |

## Owner team handoff table

| Category | Primary owner | Escalation | SLA to first-draft |
|----------|---------------|------------|--------------------|
| Security | Security Engineering lead | CISO | 48h |
| Technical | Solution Architect on deal | VP Engineering | 48h |
| Commercial | Commercial Desk analyst | CFO's office | 72h |
| Company | Corporate Marketing | CMO | 24h |
| General | Bid Manager | Head of Bids | 24h |

## Confidence scoring inputs (for classify_questions.py)

Per-question confidence is computed from:

- Number of distinct signal terms matched (each unique hit = +1).
- Signal density = matched_terms / total_words_in_question.
- Presence of an explicit category heading in the RFP (e.g. "Section 4 —
  Security") — this alone forces primary_category to SEC regardless of text.
- Conflict penalty: if signals from two categories match within 20% of each
  other, confidence drops to MEDIUM and secondary_category is populated.

Confidence bands:

| Band | Condition |
|------|-----------|
| HIGH | ≥3 distinct signals for winning category and no conflict |
| MEDIUM | 1-2 signals OR conflict penalty applied |
| LOW | 0 signals — falls through to GEN with `needs_human_triage=true` |

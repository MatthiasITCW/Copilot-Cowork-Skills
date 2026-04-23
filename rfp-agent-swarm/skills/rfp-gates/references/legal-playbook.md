# Legal Playbook

Used by Legal Counsel at Gate 2. Defines the organisation's standard position
by clause type, the deviation grading system, and the auto-flag triggers that
rfp-gates surfaces in the evidence pack.

This skill does NOT sign off on legal terms. It orchestrates the approval and
guarantees the human-review preconditions are satisfied before the gate request
is sent.

---

## 1. Standard positions by clause type

| Clause | Standard position | Acceptable range |
|---|---|---|
| Limitation of liability | Cap at 12 months' fees paid; mutual | 6–24 months' fees; mutual |
| Unlimited/uncapped carve-outs | Confidentiality breach, IP indemnity, gross negligence, wilful misconduct | Plus data-breach cap at greater of 24 months' fees or USD 5M |
| IP ownership | Each party retains pre-existing IP; customer owns customer data | Narrow licence to service; no assignment of developer IP |
| Indemnification | Mutual, fees-based cap, third-party IP claims | Add data-breach indemnity with super-cap |
| Termination for convenience | 90-day notice, no refund of prepaid unused | 60–180 days; prepaid refund negotiable case-by-case |
| Termination for cause | 30-day cure period for material breach | 15–60 days |
| Governing law | Delaware or England & Wales | New York, Singapore acceptable; otherwise escalate |
| Dispute resolution | Arbitration (AAA or LCIA), seat aligned with governing law | Courts of governing-law jurisdiction acceptable |
| Data processing addendum | Standard DPA v.current with SCCs + UK addendum | Buyer DPA acceptable if materially similar |
| Audit rights | Once per 12 months, 30 days' notice, at buyer's cost, under NDA | Shorter notice only if contractually required |
| Service levels | Tiered SLA with service credits; credits as sole remedy | Uptime floor 99.9% (standard tier) |
| Publicity | Logo rights pending mutual approval | Opt-in only for regulated buyers |

---

## 2. Deviation levels

| Level | Meaning | Gate behaviour |
|---|---|---|
| Acceptable | Within the ranges in section 1 | No flag |
| Needs Discussion | Outside the range but negotiable | Flag for Legal Counsel judgement |
| Blocker | Position the organisation will not take | Auto-fail precheck; cannot be gated |

---

## 3. Auto-flag triggers

These patterns, when detected in the buyer's RFP text or in a legal response
drafted against it, raise an automatic flag:

| Trigger | Level | Rationale |
|---|---|---|
| Uncapped liability (without carve-outs limited to standard set) | Blocker | Exposes the organisation to unbounded exposure |
| Broad IP assignment ("all IP arising from use of the service") | Blocker | Destroys reusable product IP |
| Unilateral termination for convenience by buyer with refund of prepaid + paid-but-unused services plus consequential damages | Blocker | Asymmetric exit right |
| Governing law outside Delaware/England & Wales/New York/Singapore | Needs Discussion | Jurisdictional risk requires Legal judgement |
| Buyer-imposed DPA with processor obligations more onerous than standard SCCs | Needs Discussion | May need technical change to meet |
| Audit right without NDA, notice, or cost allocation | Needs Discussion | Operational cost and confidentiality risk |
| "Most favoured customer" pricing clauses | Needs Discussion | Commercial + legal; cross-routes to Pricing Gate |
| Buyer retains ownership of "feedback" / "suggestions" | Needs Discussion | Standard position is perpetual licence to vendor |
| Perpetual indemnity for third-party claims without cap | Blocker | Uncapped economic exposure |
| Data residency promise outside service footprint | Blocker | Cannot be fulfilled technically |

---

## 4. Preconditions for the legal gate

The legal gate request is NOT sent until all of the following are true:

| Precondition | Check location |
|---|---|
| Every answer tagged `domain=legal` has `human_reviewed=true` | `review_flags.json` |
| A non-standard term list has been generated and attached | `working/non_standard_terms.json` |
| Every Blocker-level deviation has either been removed or escalated to a named senior | Legal Counsel review annotations |
| No legal answer has `source=generated` without a corresponding human review annotation | `responses.json` |

If any precondition fails, `run_gates.py` exits non-zero and the gate request is
not dispatched.

---

## 5. Non-standard term list — required shape

`working/non_standard_terms.json` must contain, for each non-standard term:

| Field | Description |
|---|---|
| `term_id` | Stable identifier |
| `clause_type` | One of the clause categories in section 1 |
| `buyer_position` | Excerpt or summary of buyer's ask |
| `our_position` | Our standard response |
| `deviation_level` | Acceptable / Needs Discussion / Blocker |
| `proposed_fallback` | Our counter, if any |
| `reviewer` | Legal team member who assessed |
| `reviewed_at_utc` | Timestamp |

---

## 6. What Legal Counsel confirms at the gate

1. The non-standard term list is complete (no missed items).
2. All Blockers have been removed, escalated, or negotiated out.
3. Deviations at Needs Discussion level are acceptable for this buyer and this
   deal size.
4. The final legal responses read defensibly and consistently.
5. No answer creates an obligation the organisation cannot meet.

Legal Counsel approval signature captures identity, UTC timestamp, and the
version hash of `responses.json` that was reviewed.

---

## 7. Escalation

| Situation | Escalate to |
|---|---|
| Blocker that Legal Counsel believes the organisation should consider accepting for strategic reasons | General Counsel + CRO |
| Novel jurisdiction (e.g. first-time sovereign buyer) | General Counsel |
| Cross-gate collision (e.g. pricing MFN clause) | Legal Counsel + AE jointly |

---

## 8. Out of scope for this gate

- Line-level redlining — that is legal-redliner.
- Bid/no-bid commercial risk assessment — rfp-fit-assessment.
- Certification-language review — Security Gate.

---

## Cross-references

- `../SKILL.md`
- `../scripts/run_gates.py`
- `security-completeness-checklist.md`
- `gate-rejection-routing.md`

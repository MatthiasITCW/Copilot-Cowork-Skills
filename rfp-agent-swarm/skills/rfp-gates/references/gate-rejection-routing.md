# Gate Rejection Routing

Defines where a rejected gate result is routed, the rework service level, and
the escalation path when a gate stalls.

Rejections are a normal outcome — they are the gate working as designed. Every
rejection is logged to `working/gate_audit.json` and fed to rfp-answer-bank
(lessons learned) and skill-factory (precheck refinement).

---

## 1. Routing decision table

| Gate | Rejection reason (code) | Routed to | Artefact used |
|---|---|---|---|
| Security | SEC_MISSING | rfp-respond | `gate-rejection-notice.md` |
| Security | CERT_UNVERIFIED | rfp-respond + SecOps | `gate-rejection-notice.md` |
| Security | AUDIT_DATE_UNVERIFIED | SecOps (then rfp-respond) | `gate-rejection-notice.md` |
| Security | RESIDENCY_CONFLICT | Product + rfp-respond | `gate-rejection-notice.md` |
| Security | CRYPTO_UNAPPROVED | rfp-respond | `gate-rejection-notice.md` |
| Security | SEC_GENERATED_UNREVIEWED | rfp-review + rfp-respond | `gate-rejection-notice.md` |
| Legal | human_reviewed=false | rfp-review | `gate-rejection-notice.md` |
| Legal | Blocker clause unresolved | legal-redliner | `gate-rejection-notice.md` |
| Legal | Non-standard term list incomplete | rfp-review | `gate-rejection-notice.md` |
| Legal | Novel jurisdiction | General Counsel (escalation) | direct escalation note |
| Pricing | PRICING_GENERATED | Pricing Ops | `gate-rejection-notice.md` |
| Pricing | PRICING_UNLINKED | Pricing Ops | `gate-rejection-notice.md` |
| Pricing | PRICING_INPUT_UNKNOWN | Pricing Ops | `gate-rejection-notice.md` |
| Pricing | PRICING_VERSION_STALE | Pricing Ops | `gate-rejection-notice.md` |
| Pricing | PRICING_DISCOUNT_UNAUTHORISED | Account Exec + authorising role | `gate-rejection-notice.md` |
| Pricing | PRICING_BUNDLE_UNAUTHORISED | Pricing Ops + Finance | `gate-rejection-notice.md` |

---

## 2. Rework SLA

The rework SLA is measured from the time the rejection notice is sent to the
time the originating team resubmits a fixed response package.

| Severity | SLA |
|---|---|
| Single-item correction (e.g. cert name typo) | 4 business hours |
| Scoped rework (under 10 items) | 1 business day |
| Wide rework (10+ items or cross-functional) | 3 business days |
| Blocker-level legal deviation requiring negotiation | Case-by-case, tracked on deal |

If the RFP deadline is tighter than the SLA, the AE flags the bid to the deal
review forum. The gate does NOT auto-loosen the SLA.

---

## 3. Escalation path (gate stalled)

A gate is considered stalled if no approver response is received within the
stated window.

| Window | Action |
|---|---|
| 0–4h no response | Normal pending |
| 4–8h no response | Nudge via Teams (automated) |
| 8–16h no response | Pager-style ping + backup approver named on the gate |
| 16h+ no response | Escalate to approver's line manager; notify AE and RFP programme owner |
| 24h+ no response AND deadline at risk | Deal review forum; no auto-approval under any circumstance |

Backup approvers are configured in `working/gate_approvers.json`. A backup
approver has the same authority as the primary but is used only when primary
is unavailable and the stall threshold has been reached.

---

## 4. Rejection audit record shape

Every rejection writes one record to `working/gate_audit.json`:

| Field | Description |
|---|---|
| `event_id` | UUID |
| `gate` | security \| legal \| pricing |
| `rfp_id` | Source RFP identifier |
| `rejected_by` | Approver identity |
| `rejected_by_role` | Role (Security Lead / Legal Counsel / Account Exec) |
| `reason_code` | Code from the routing table |
| `reason_text` | Free-text reason (mandatory in the card) |
| `affected_questions` | Array of question IDs |
| `rework_routed_to` | Team or skill per routing table |
| `rework_sla_hours` | From section 2 |
| `rejected_at_utc` | Timestamp |
| `source_precheck_hash` | SHA of the precheck JSON that preceded the rejection |
| `response_version_hash` | SHA of `responses.json` at rejection time |

---

## 5. Learning loop

Once a week, rfp-answer-bank reads rejections grouped by `reason_code` and:

1. Identifies recurring content defects (e.g. repeated CERT_UNVERIFIED on the
   same cert name).
2. Proposes answer-bank edits for SME review.
3. Flags precheck gaps to skill-factory (e.g. if rejections keep surfacing a
   class the precheck should have caught).

---

## 6. Re-submission flow

| Step | Who | What |
|---|---|---|
| 1 | Originating team | Fixes the items listed in `affected_questions` |
| 2 | rfp-review | Re-runs human review where the fix touched legal content |
| 3 | rfp-gates | Runs `run_gates.py` again (fresh precheck) |
| 4 | rfp-gates | Sends only the previously-rejected gate, not the already-approved ones, unless a material change affects them |
| 5 | Approver | Approves or rejects again |

The approvals already granted on other gates remain valid as long as
`response_version_hash` has not changed on scope within those gates.

---

## Cross-references

- `../SKILL.md`
- `../assets/gate-rejection-notice.md`
- `../scripts/gate_status_tracker.py`
- `security-completeness-checklist.md`
- `legal-playbook.md`
- `pricing-authorization-rules.md`

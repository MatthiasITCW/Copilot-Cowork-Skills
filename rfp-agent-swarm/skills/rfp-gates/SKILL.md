# rfp-gates

Step 4 of the RFP Agent Swarm. Orchestrates three NON-NEGOTIABLE human approval
gates — Security Completeness, Legal Review, and Pricing Approval — before an
RFP response package is allowed to progress to assembly and final submit.

This skill does NOT make approval decisions. It prepares evidence, dispatches
Teams adaptive-card approval requests to named approvers, tracks responses, and
aggregates a blocking go/no-go verdict. The pipeline remains paused until all
three gates return Approved. Any rejection routes back to the originating team
with a structured reason and is logged to the audit trail.

---

## When to use this skill

Invoke rfp-gates after rfp-respond has produced a tiered `responses.json` and
rfp-review has attached human-reviewed flags to legal responses. Invoke it
before rfp-assemble runs.

### Triggers

- "run quality gates"
- "security gate check"
- "legal review gate"
- "pricing approval gate"
- "QA this RFP response"
- "gate sign-off"
- "send for gate approval"
- "run RFP compliance check"
- "send approvals for this bid"
- "gate this response package"

### Do NOT use for

- Drafting answers — that is rfp-respond.
- Line-level editing of a specific legal clause — that is legal-redliner.
- Producing the final PDF — that is rfp-assemble.
- Deciding whether to bid at all — that is rfp-fit-assessment.
- Populating the answer bank with approved content — that is rfp-answer-bank.
- Internal narrative Q&A about pricing strategy — that is a deal-room task.

---

## Design principles applied here

| Principle | How rfp-gates enforces it |
|---|---|
| Safety over speed | Pipeline pauses on any missing gate response. No auto-approve path. |
| Transparency | Every precheck finding, rejection, and approval is written to `working/gate_audit.json`. |
| Hard gates cannot be overridden | There is no `--force` flag, no skip, no bypass token. Deadline pressure does not unlock the gates. |
| Named accountability | Each gate has one named approver role; approvals capture identity and timestamp. |
| Human-in-the-loop | Automation produces the evidence pack; a human renders the verdict. |

---

## Built-In Skills Used

| Cowork Skill | How this skill uses it |
|---|---|
| Adaptive Cards | Render the live 3-gate dashboard and each per-gate approval request card with Approve/Reject buttons. |
| Email | Dispatch gate approval requests (with embedded Adaptive Card) to named approvers when Teams is not the preferred channel. |
| Communications | Send structured rejection notifications back to the owning team (rfp-respond, SecOps, Pricing Ops, legal-redliner). |
| Excel | Append audit events to `output/rfp-<rfp_id>/audit-log.xlsx`; read `authorised_pricing_inputs` and `approved_certs` workbooks. |
| Calendar Management | Run SLA countdown against each gate's approver and surface overdue approvals. |
| Scheduling | Book an escalation meeting when a gate reviewer misses SLA or flags a novel risk. |
| Meetings | Prepare a legal-review session prep-note (agenda, flagged clauses, precheck evidence) when a synchronous review is required. |
| Enterprise Search | Look up historical approver decisions and prior rejection reasons for the current buyer / clause type. |

---

## Inputs, outputs, and file contract

### Inputs

| File | Producer | Purpose |
|---|---|---|
| `working/responses.json` | rfp-respond | Tiered answers with source + review flags |
| `working/approved_certs.json` | org data | Authoritative certifications list |
| `working/approved_audits.json` | org data | Authoritative audit dates |
| `working/authorised_pricing_inputs.json` | Pricing Ops | Allowed pricing input IDs + versions |
| `working/review_flags.json` | rfp-review | `human_reviewed` booleans for legal items |

### Outputs

| File | Purpose |
|---|---|
| `working/gate_precheck.json` | Automated evidence pack for each gate |
| `working/approval_request.json` | Teams adaptive-card payload per gate |
| `working/gate_verdict.json` | Aggregate go/no-go and rejection details |
| `working/gate_audit.json` | Append-only audit trail |

---

## Sequence diagram (parallel approvals, single blocking aggregator)

```
  rfp-respond -> responses.json
       |
       v
 +-------------+
 | run_gates   |  automated prechecks (security, legal, pricing)
 +-------------+
       | gate_precheck.json
       v
 +---------------------+---------------------+---------------------+
 |                     |                     |                     |
 v                     v                     v                     v
 send_gate_approval    send_gate_approval    send_gate_approval
 (security)            (legal)               (pricing)
 -> Security Lead      -> Legal Counsel      -> Account Exec
 (Teams card)          (Teams card)          (Teams card)
 |                     |                     |
 v                     v                     v
 Approved / Rejected   Approved / Rejected   Approved / Rejected
 +---------------------+---------------------+
                       |
                       v
               gate_status_tracker
                       |
         +-------------+-------------+
         |                           |
         v                           v
    ALL APPROVED                ANY REJECTED
         |                           |
         v                           v
    rfp-assemble             gate-rejection-notice
                             -> originating team
                             pipeline stays paused
```

---

## Workflow

1. Run `scripts/run_gates.py` to produce automated prechecks. Non-zero exit if
   any auto-fail condition is hit; the gate request is not sent until those
   blockers are resolved by the originating team.
2. For each of the three gates, run `scripts/send_gate_approval.py` to build
   the adaptive-card payload. In production, a Power Automate flow sends the
   card; locally, the payload is rendered via `render-ui`.
3. Approvers respond in Teams. Their response (Approved or Rejected with
   mandatory comment) is written to `working/gate_statuses.json`.
4. `scripts/gate_status_tracker.py` aggregates statuses. Verdict is PASS only
   if all three gates are Approved.
5. On rejection, `assets/gate-rejection-notice.md` is routed to the team owning
   the defect (see `references/gate-rejection-routing.md`).

---

## Usage

```bash
# 1. Evidence pack
python scripts/run_gates.py \
  --responses working/responses.json \
  --approved-certs working/approved_certs.json \
  --pricing-inputs working/authorised_pricing_inputs.json \
  --output working/gate_precheck.json

# 2. Build approval cards (one per gate)
python scripts/send_gate_approval.py \
  --gate security --precheck working/gate_precheck.json \
  --approver-email security.lead@example.com \
  --output working/approval_request_security.json

python scripts/send_gate_approval.py \
  --gate legal --precheck working/gate_precheck.json \
  --approver-email legal.counsel@example.com \
  --output working/approval_request_legal.json

python scripts/send_gate_approval.py \
  --gate pricing --precheck working/gate_precheck.json \
  --approver-email account.exec@example.com \
  --output working/approval_request_pricing.json

# 3. After approvers respond, aggregate
python scripts/gate_status_tracker.py \
  --statuses working/gate_statuses.json \
  --output working/gate_verdict.json
```

---

## Gate definitions

| Gate | Approver | Auto-fail triggers | Manual judgement |
|---|---|---|---|
| Security Completeness | Security Lead | Missing answer, unverifiable cert, fabricated audit date | Residual residency, sub-processor currency, IR commitments |
| Legal Review | Legal Counsel | `human_reviewed=false` on any legal item, non-standard clause unflagged | Acceptability of deviations, novel jurisdictional risk |
| Pricing Approval | Account Executive | `source=generated`, missing `pricing_input_id`, discount beyond tier without auth | Commercial acceptability, strategic discounting |

---

## Rejection handling

See `references/gate-rejection-routing.md`. Summary:

| Gate | Typical rejection cause | Routed to |
|---|---|---|
| Security | Cert claim not in approved list | rfp-respond + SecOps |
| Security | Missing answer | rfp-respond |
| Legal | Clause outside playbook | legal-redliner |
| Legal | No human review flag | rfp-review |
| Pricing | AI-generated figure | Pricing Ops |
| Pricing | Discount beyond authorisation | Account Exec + Finance |

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| `run_gates.py` exits non-zero with CERT_UNVERIFIED | Answer references a cert not in `approved_certs.json` | Re-draft via rfp-respond with an approved cert; do not add to the approved list without SecOps sign-off. |
| Legal gate precheck flags every item | `review_flags.json` not produced by rfp-review | Re-run rfp-review; rfp-gates cannot proceed without human review markers. |
| Pricing precheck flags `source=generated` | Pricing response was authored by the LLM rather than structured from authorised inputs | Reject; send back to Pricing Ops to restructure from `authorised_pricing_inputs.json`. |
| No response from approver after SLA window | Teams card not delivered or approver out of office | Escalate per `references/gate-rejection-routing.md` escalation path; do not auto-approve. |
| `gate_status_tracker.py` reports Pending indefinitely | `gate_statuses.json` not being updated by Power Automate flow | Check flow run history; replay the webhook if necessary. |
| Verdict PASS but audit trail missing an approver signature | Status file hand-edited without signature block | Invalidate the verdict; require re-approval. |
| Discount tier calculation appears wrong | Tier thresholds misaligned with `pricing-authorization-rules.md` | Update the rules reference first, then rerun — never patch the script to match a one-off deal. |

---

## Audit and learning loop

Every rejection is captured with:

- `gate` (security | legal | pricing)
- `rejected_by` (approver identity)
- `reason` (free text, mandatory in the card)
- `affected_questions` (array of question IDs)
- `timestamp_utc`

This feed is consumed by rfp-answer-bank to prevent the same defect recurring,
and by skill-factory to refine the prechecks in `run_gates.py`.

---

## Audit Log

All gate lifecycle events are written as immutable rows to
`output/rfp-<rfp_id>/audit-log.xlsx` via the Excel built-in skill. Each row is
appended — NEVER updated or deleted — so that a rejection followed by a
re-submission and subsequent approval appears as three separate events with
three distinct timestamps.

| Event Type | When | Actor | Key fields |
|---|---|---|---|
| GATE_REQUESTED | Approval request sent via Teams/Email | AI | gate (Security/Legal/Pricing), approver, request_timestamp |
| GATE_APPROVED | Approver clicks Approve | human | gate, approver, comments, decision_timestamp |
| GATE_REJECTED | Approver rejects | human | gate, approver, rejection_reason, affected_question_ids |
| PIPELINE_PAUSED | Any gate is outstanding | AI | gates_pending |
| PIPELINE_RESUMED | All gates approved | AI | all_gate_timestamps |

Schema and helper:

- [audit-log-schema.md](../rfp-answer-bank/references/audit-log-schema.md) — canonical column order, types, and validation rules.
- [append_audit.py](../rfp-answer-bank/scripts/append_audit.py) — append-only writer; refuses to modify existing rows.

Immutability rule: gate events are IMMUTABLE. Rejections are captured as
events in their own right; a subsequent approval does NOT overwrite the
rejection row. A new event row is written for each re-submission cycle so
that the full decision history — including every reversal — is reconstructible
from the log alone.

---

## Adaptive Card Dashboard

Rendered via the Adaptive Cards built-in skill. Two surfaces: a live dashboard
card that tracks the three gates in one view, and a per-gate approval-request
card that carries the Approve/Reject buttons.

### Live 3-gate dashboard card

Three status tiles — Security / Legal / Pricing — rendered side-by-side. Each
tile shows:

- Approver name (pulled from the gate definition table)
- Status badge: Pending | Approved | Rejected
- Timestamp of the most recent event for that gate

The dashboard refreshes on every new row appended to `audit-log.xlsx`.

### On rejection

The offending tile expands inline to surface:

- The rejection reason (mandatory free-text captured from the approver)
- A list of affected question IDs, each a deep-link routed back to rfp-respond
  for rework

No other tiles are cleared; approved gates remain Approved. Only the rejected
gate must be re-submitted once rework is complete.

### On all-approved

A pipeline-resumed card replaces the dashboard, showing:

- All three approver names and their individual `decision_timestamp` values
- The aggregate `PIPELINE_RESUMED` timestamp
- An auto-advance CTA button: "Assemble the submission package" (invokes
  rfp-assemble)

### Per-gate approval-request card

Each gate's approval request is itself an Adaptive Card, dispatched via Email
or Teams. Every card carries Approve and Reject buttons (Reject is disabled
until a reason is entered) plus the gate-specific context pack:

| Gate | Context embedded in the card |
|---|---|
| Security | Question summary + precheck evidence (cert list, audit dates, unverified claims) |
| Legal | Question summary + non-standard-clause flag table with playbook deviation notes |
| Pricing | Question summary + reference to the authorised pricing sheet and the tier/discount calculation |

---

## Boundaries

- rfp-gates NEVER signs off on behalf of a human approver.
- rfp-gates NEVER generates pricing, legal positions, or security claims.
- rfp-gates NEVER modifies `responses.json`; it only reads and evaluates.
- rfp-gates NEVER bypasses a gate for deadline reasons.

---

## Related Skills

### RFP chain

`rfp-intake → rfp-fit-assessment → rfp-respond → THIS SKILL → rfp-review → rfp-assemble`

- THIS SKILL is the **non-negotiable checkpoint** in the chain. It cannot be
  bypassed, skipped, or auto-advanced under deadline pressure. There is no
  `--force` flag.
- On **rejection**, control routes back to rfp-respond for ONLY the affected
  questions (carried by `affected_question_ids` on the `GATE_REJECTED` event).
  Previously approved gates do not need re-approval unless the rework changes
  their scope.
- On **all-approved**, the pipeline unlocks rfp-assemble — which will refuse
  to run until a `PIPELINE_RESUMED` event is present in the audit log.

| Skill | Relationship |
|---|---|
| rfp-intake | Upstream: establishes the RFP ID, deadline, buyer context. |
| rfp-fit-assessment | Upstream: bid/no-bid decision precedes all drafting. |
| rfp-respond | Upstream: produces `responses.json` consumed here; receives rejection routing. |
| rfp-review | Upstream: attaches `human_reviewed` flags to legal items. |
| rfp-assemble | Downstream: runs only if rfp-gates returns PASS. |
| rfp-answer-bank | Lateral: consumes rejection reasons for learning loop; hosts shared audit log schema. |
| legal-redliner | Lateral: receives legal-gate rejections for clause rework. |
| legal-review | Lateral: deeper clause-level review preceding the gate. |
| audit-readiness | Consumer: gate audit trail feeds compliance evidence. |
| skill-factory | Consumer: precheck miss data used to tune rules. |

### Cowork built-ins leveraged

| Built-in | Role in rfp-gates |
|---|---|
| Adaptive Cards | Renders the gate approval request cards (Approve/Reject) and the live 3-gate dashboard. |
| Email | Sends each gate approval request to the named approver. |
| Communications | Pushes rejection notifications (with reason and affected question IDs) to the owning team. |
| Excel | Appends every gate event to `audit-log.xlsx`; reads the authorised pricing sheet. |
| Calendar Management | SLA countdown per gate; surfaces overdue approvals. |
| Scheduling | Books an escalation meeting if a gate reviewer needs to convene stakeholders. |
| Meetings | Produces prep notes (agenda, flagged clauses, precheck evidence) for the legal review session. |

---

## Cross-references

- `references/security-completeness-checklist.md`
- `references/legal-playbook.md`
- `references/pricing-authorization-rules.md`
- `references/gate-rejection-routing.md`
- `scripts/run_gates.py`
- `scripts/send_gate_approval.py`
- `scripts/gate_status_tracker.py`
- `assets/gate-approval-request-template.md`
- `assets/gate-rejection-notice.md`

# Security Completeness Checklist

Used by the Security Lead at Gate 1. The items below must all be verifiable
before approval is granted. The precheck in `scripts/run_gates.py` automates
the machine-checkable items; the Security Lead renders judgement on the
remaining ones.

---

## 1. Answer completeness

| Check | Machine-checkable | Source |
|---|---|---|
| Every question tagged `domain=security` has a non-empty `answer` field | Yes | `responses.json` |
| No answer contains `[TODO]`, `[PLACEHOLDER]`, or `TBC` markers | Yes | `responses.json` |
| Every answer has a `source` of `answer-bank`, `sme-authored`, or `structured-from-policy` — never `generated` without review | Yes | `responses.json` |
| Every answer has a `last_reviewed_utc` within the answer-bank retention window | Yes | `responses.json` + `answer_bank_metadata.json` |

---

## 2. Certification claims

A response may reference a certification only if that certification appears in
the approved certs list. The approved list is the organisation's authoritative
record of currently-held certifications. Examples the list may contain include
(subject to the organisation's actual holdings):

- SOC 2 Type II
- ISO/IEC 27001
- ISO/IEC 27701
- ISO/IEC 27017
- ISO/IEC 27018
- PCI DSS
- HIPAA (attestation)
- FedRAMP (Moderate / High)

| Check | Rule |
|---|---|
| Cert name match | String must match a `name` entry in `approved_certs.json` exactly (case-insensitive). |
| Cert validity | `approved_certs.json` entry must show `status=active` and `expires_on > today`. |
| Scope match | Any scope claim in the answer must match the `scope` field on the cert record. |
| Audit date | If the answer cites an audit date, it must match the date in `approved_audits.json`. |

Any variance is a hard auto-fail (CERT_UNVERIFIED or AUDIT_DATE_UNVERIFIED).

---

## 3. Data residency claims

Data residency claims describe where customer data is stored, processed, and
backed up. These must match the product's current deployment reality.

| Claim type | Verification source |
|---|---|
| Primary storage region | Product architecture register |
| Backup region | DR runbook |
| Processing region | Service topology map |
| Transit through other regions | Network routing matrix |

Security Lead confirms the answer does not overclaim (e.g. asserting EU-only
when a global CDN is in the path).

---

## 4. Sub-processor list

| Check | Rule |
|---|---|
| The sub-processor list referenced in the response matches the current published list | Source of truth: Trust Centre page + DPA annex |
| Any sub-processor added in the last 30 days is disclosed | Per contractual notification obligations |
| No deprecated sub-processor appears | Deprecation log |

---

## 5. Incident response commitments

| Check | Rule |
|---|---|
| Notification window claimed matches the standard MSA | 72 hours unless a customer-specific rider is in force |
| Breach definition aligns with standard language | No narrower definition without Legal sign-off |
| Forensics retention period matches policy | 12 months default |

---

## 6. Cryptography claims

| Check | Rule |
|---|---|
| Algorithms named are on the approved algorithm list | e.g. AES-256-GCM, TLS 1.2+, RSA-2048+ or ECDSA P-256+ |
| Key management model matches implementation | HSM, KMS, BYOK, HYOK — must match what the product actually offers |
| No claim of "quantum-safe" unless product genuinely implements a PQC-ready suite | Hard fail otherwise |

---

## 7. Access controls and identity

| Check | Rule |
|---|---|
| SSO protocols listed (SAML 2.0, OIDC) match product capability | Product capability matrix |
| MFA enforcement claim matches actual policy | Admin policy register |
| Role-based access granularity claim matches UI/API reality | RBAC matrix |

---

## Decision table — auto-fail conditions

| Condition | Code | Auto-fail? |
|---|---|---|
| Security question with empty answer | SEC_MISSING | Yes |
| Cert claim not in `approved_certs.json` | CERT_UNVERIFIED | Yes |
| Audit date not in `approved_audits.json` | AUDIT_DATE_UNVERIFIED | Yes |
| Answer `source=generated` without `human_reviewed=true` | SEC_GENERATED_UNREVIEWED | Yes |
| Residency claim conflicts with architecture register | RESIDENCY_CONFLICT | Needs Security Lead judgement |
| Sub-processor list older than 30 days | SUBP_STALE | Flag for review |
| Unapproved cryptographic algorithm | CRYPTO_UNAPPROVED | Yes |
| IR notification window narrower than MSA default | IR_TIGHTER_THAN_MSA | Needs Legal + Security Lead |

---

## Signature requirements

Security Lead approval must capture:

- Approver full name and role
- UTC timestamp
- A statement that the certification claims, audit dates, and residency
  assertions have been checked against authoritative sources
- Any conditions attached to the approval (e.g. "approved subject to
  Q47 adding a residency caveat")

The signature block is stored in `working/gate_audit.json` under
`security.signature`.

---

## Out of scope for this checklist

- Contractual liability caps — Legal Gate.
- Pricing of security add-ons (e.g. HYOK surcharge) — Pricing Gate.
- Marketing claims about roadmap — product marketing review.

---

## Cross-references

- `../SKILL.md`
- `../scripts/run_gates.py`
- `gate-rejection-routing.md`

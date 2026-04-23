# Fit Scoring Rubric

Concrete 0-5 anchors for every scorecard dimension. Use this document when
populating `working/scorecard.json`. Every score outside the 2-4 middle band
REQUIRES a 1-2 sentence evidence string in the JSON so it can appear in the
memo.

Weights (enforced by `scripts/compute_fit_score.py`):

| # | Dimension | Weight |
|---|---|---|
| 1 | KB Match Rate (estimated) | 25 |
| 2 | Technical Fit | 20 |
| 3 | Commercial Fit | 15 |
| 4 | Competitive Positioning | 10 |
| 5 | Strategic Alignment | 10 |
| 6 | Resource Availability | 10 |
| 7 | Deadline Feasibility | 10 |
| — | **Total** | **100** |

Raw dimension scores are on a 0-5 scale. The script converts each to a
0-100 dimension value via `dimension_value = raw * 20`, then multiplies by
the weight and divides by 100. The weighted total is the sum, rounded to
one decimal place (0.0-100.0).

---

## 1. KB Match Rate (estimated) — weight 25

Source: `scripts/kb_match_estimator.py` output `overall_estimate_pct`.

| Raw | Anchor |
|---|---|
| 5 | >=80% of classified questions map to HIGH-confidence prior answers |
| 4 | 65-79% HIGH or HIGH+MEDIUM combined |
| 3 | 50-64% MEDIUM-confidence average |
| 2 | 35-49% with many NEW-category questions |
| 1 | 20-34% — mostly NEW content, heavy SME load expected |
| 0 | <20% — effectively a custom proposal |

Evidence format: `"est_pct": 68, "confidence": "MEDIUM", "notes": "..."`.

## 2. Technical Fit — weight 20

How well the buyer's stated technical requirements map to our product
capabilities (features, integrations, standards).

| Raw | Anchor |
|---|---|
| 5 | All "must" requirements natively supported; >=90% of "should" supported |
| 4 | All "must" supported; 70-89% of "should" supported |
| 3 | 1-2 "must" requirements require a workaround; most "should" supported |
| 2 | 3+ "must" requirements require workarounds OR a roadmap promise |
| 1 | Core "must" requirement unsupported and not on near-term roadmap |
| 0 | Fundamental architectural mismatch (e.g. on-prem only, we are SaaS) |

## 3. Commercial Fit — weight 15

Deal size vs floor, pricing model alignment, contract-term feasibility
(payment terms, liability caps, SLAs, indemnity).

| Raw | Anchor |
|---|---|
| 5 | Deal >=2x floor; pricing model matches list; standard MSA accepted |
| 4 | Deal >=1.5x floor; minor pricing alignment; light redlines expected |
| 3 | Deal at floor; pricing workable; moderate redlines (cap, SLAs) |
| 2 | Deal just below floor OR heavy redlines (uncapped liability requested) |
| 1 | Deal well below floor OR non-negotiable terms we cannot accept |
| 0 | Commercially impossible (e.g. unlimited indemnity, free pilot demand) |

## 4. Competitive Positioning — weight 10

Incumbent presence, known shortlist, our historic win rate against that
set, and strength of differentiators. See
`competitive-positioning-playbook.md` for inference heuristics.

| Raw | Anchor |
|---|---|
| 5 | Sole-source or clear front-runner; no strong incumbent |
| 4 | Shortlist favourable; our historic win rate >60% vs named competitors |
| 3 | Open field; win rate 40-60%; differentiators credible |
| 2 | Incumbent present but fatigued; our win rate 25-40% |
| 1 | Strong incumbent OR competitor with clear product advantage |
| 0 | RFP text appears written to an incumbent's spec sheet |

## 5. Strategic Alignment — weight 10

Target vertical, logo value, reference-ability, regional priorities, fit
with current quarter/year sales strategy.

| Raw | Anchor |
|---|---|
| 5 | Named strategic logo / tier-1 target vertical / marquee reference |
| 4 | Target vertical; referenceable; expansion potential clear |
| 3 | Adjacent vertical; modest strategic value |
| 2 | Non-priority vertical; limited reference value |
| 1 | Off-strategy; would divert from stated priorities |
| 0 | Actively conflicts with a strategic partnership or exclusivity |

## 6. Resource Availability — weight 10

SME and proposal-team capacity during the response window. Cross-check
with Proposal Ops capacity tracker.

| Raw | Anchor |
|---|---|
| 5 | All named SMEs confirmed available; proposal lead has headroom |
| 4 | SMEs available with minor conflicts; proposal lead full but workable |
| 3 | 1 critical SME partially booked; manageable with reshuffle |
| 2 | 2+ critical SMEs conflicted; proposal lead over-allocated |
| 1 | Key SME unavailable for >50% of window |
| 0 | No proposal lead available at all during the window |

## 7. Deadline Feasibility — weight 10

Runway in working hours from "now" to deadline vs estimated effort from
the task list produced by `rfp-intake`.

| Raw | Anchor |
|---|---|
| 5 | Runway >=2.0x estimated effort |
| 4 | Runway 1.5-2.0x |
| 3 | Runway 1.2-1.5x — workable with focus |
| 2 | Runway 1.0-1.2x — tight, no slippage allowed |
| 1 | Runway 0.8-1.0x — would require overtime / re-scoping |
| 0 | Runway <0.8x estimated effort |

---

## Weighting Formula

```
dimension_value_i   = raw_i * 20                      (0-100)
contribution_i      = dimension_value_i * weight_i / 100
weighted_total      = sum(contribution_i) over i in {1..7}
```

Rounded to one decimal. Band:

- `weighted_total >= 75.0` -> **Go** (recommend)
- `50.0 <= weighted_total < 75.0` -> **Conditional**
- `weighted_total < 50.0` -> **No-Go** (recommend)

## Worked Example

Acme HealthCo, 142 questions, deadline 2026-05-20.

| # | Dimension | Raw | Value | Weight | Contribution |
|---|---|---|---|---|---|
| 1 | KB Match | 4 | 80 | 25 | 20.00 |
| 2 | Technical Fit | 4 | 80 | 20 | 16.00 |
| 3 | Commercial Fit | 3 | 60 | 15 | 9.00 |
| 4 | Competitive | 3 | 60 | 10 | 6.00 |
| 5 | Strategic | 4 | 80 | 10 | 8.00 |
| 6 | Resource | 3 | 60 | 10 | 6.00 |
| 7 | Deadline | 3 | 60 | 10 | 6.00 |
| — | **Total** | — | — | **100** | **71.00** |

Weighted total 71.0 -> **Conditional**. Memo would flag Commercial Fit
(contract redlines) and Deadline (1.3x runway) as top risks.

## Calibration Notes

- Two reviewers scoring the same dimension within +/- 1 is acceptable.
- Differences of 2+ require a calibration conversation using this rubric.
- Evidence strings are mandatory for any raw score of 0, 1, or 5.
- Re-score after any material new information (e.g. AE Q&A received back).

---

## Kill Criteria (Auto-Flag, Human-Confirmed)

Trigger any row below and the memo raises a `KILL_CRITERIA_FLAGGED` notice.
The human decision owner still signs; the flag does not auto-decline.

| Criterion | Signal in RFP text / metadata | Rationale |
|---|---|---|
| Missing mandatory certification | "Respondent MUST hold [FedRAMP High / IRAP / C5 / etc]" | Legal exposure / disqualification |
| Data residency infeasible | "Data must reside in-country with no egress" (region we don't run) | Architectural blocker |
| Deal below commercial floor | Estimated TCV < Deal Desk floor from policy | Unit economics |
| Non-negotiable uncapped liability | "Liability shall not be limited" | Insurance / policy violation |
| Exclusive incumbent renewal lock | Contract language references existing multi-year auto-renew with competitor | Low win probability |
| Conflicting partner exclusivity | Buyer is an exclusivity counterparty of a strategic partner | Channel conflict |
| Unacceptable IP terms | "All work product and background IP assign to buyer" | IP policy violation |
| Timeline impossible | Runway < 0.5x estimated effort from task list | Physically infeasible |

Each fired criterion MUST be rendered as a bullet in the memo
`Risks & Mitigations` section with the text "KILL CRITERION — HUMAN REVIEW".

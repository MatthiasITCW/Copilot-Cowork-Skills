# Analytics Report Template

The analytics report is the companion artefact that makes the RFP Agent Swarm's
work visible. It is produced in two shapes from the same JSON output of
`scripts/generate_analytics_report.py`:

| Shape | When to use | Rendered by |
|:---|:---|:---|
| Word (.docx) | Detailed read-only record attached to the submission | `docx` skill |
| PowerPoint (.pptx) | Exec-visibility deck for leadership review | `pptx` skill |

Both shapes share the same section ordering. Only layout differs.

---

## 1. Section Structure

| # | Section | Purpose |
|:---:|:---|:---|
| 1 | Exec summary (1 page / 1 slide) | Top-line numbers for leadership |
| 2 | Match rate breakdown | HIGH / MEDIUM / LOW plus by category |
| 3 | Confidence distribution | Donut chart of responses by tier |
| 4 | Gate outcomes | Pass / reject counts and timestamps |
| 5 | Effort metrics | SME hours saved, total turnaround |
| 6 | Learning-loop stats | New KB entries, corrections logged |
| 7 | Provenance audit | Every answer traced to source or generated |
| 8 | Trend comparison | Vs prior N RFPs (if history exists) |

---

## 2. Section 1 — Exec Summary

| Metric | Source |
|:---|:---|
| RFP title / buyer / ID | RFP metadata |
| Total questions | `len(responses)` |
| Match rate | `%HIGH + %MEDIUM` |
| Gate outcomes | 3 icons: pass / pass / pass |
| Turnaround (hours) | `submit_time - ingest_time` |
| SME hours saved | Computed in `generate_analytics_report.py` |

Layout:

- Word: 1-page summary with a 2-column layout
- PowerPoint: 1 slide, big-number grid (6 KPIs)

---

## 3. Section 2 — Match Rate Breakdown

### Overall bar chart

| Tier | Count | % |
|:---|:---:|:---:|
| HIGH (≥ 90%) | n_high | `n_high / total` |
| MEDIUM (75–89%) | n_medium | `n_medium / total` |
| LOW (< 75%, generated) | n_low | `n_low / total` |

### By category (one row per category)

| Category | Total | HIGH | MEDIUM | LOW |
|:---|:---:|:---:|:---:|:---:|
| Security | … | … | … | … |
| Technical | … | … | … | … |
| Commercial | … | … | … | … |
| Company | … | … | … | … |

---

## 4. Section 3 — Confidence Distribution (Donut)

Donut chart with three slices using the brand colours:

| Slice | Colour token |
|:---|:---|
| HIGH | `colour.success` |
| MEDIUM | `colour.warning` |
| LOW | `colour.danger` |

Accessible alt text is required — include the three percentages in the alt
text so screen readers can convey the data.

---

## 5. Section 4 — Gate Outcomes

| Gate | Approver | Timestamp | Outcome |
|:---|:---|:---|:---|
| Security completeness | … | ISO-8601 | Approved / Rejected |
| Legal review | … | ISO-8601 | Approved / Rejected |
| Pricing approval | … | ISO-8601 | Approved / Rejected |

If any gate shows Rejected, the report explicitly highlights that assemble
must not have proceeded — this is a red flag for the audit trail.

Rejection count (cumulative): aggregated across any re-runs during this RFP.

---

## 6. Section 5 — Effort Metrics

| Metric | Formula |
|:---|:---|
| Total questions | `len(responses)` |
| KB-matched (HIGH + MEDIUM) | `n_high + n_medium` |
| Generated (LOW) | `n_low` |
| Estimated SME minutes per question (baseline) | `baseline_minutes` (from metadata; default 15) |
| SME minutes saved (KB-matched) | `(n_high + n_medium) × baseline_minutes` |
| SME hours saved | `minutes_saved / 60` |
| Turnaround (hours) | `submit_time - ingest_time` |

Example formatting for the Word version:

| Metric | Value |
|:---|---:|
| Total questions | 184 |
| KB-matched | 151 (82%) |
| Generated | 33 (18%) |
| SME minutes saved | 2,265 |
| **SME hours saved** | **37.8** |
| Turnaround | 46 h |

---

## 7. Section 6 — Learning-Loop Stats

| Metric | Source |
|:---|:---|
| New KB entries added | Corrections log `action: new_entry` count |
| Existing entries updated | Corrections log `action: update` count |
| Corrections logged (total) | `len(corrections)` |
| Avg confidence delta on corrections | Mean of `new_confidence - old_confidence` |

These numbers flow downstream to `rfp-answer-bank` — cross-link that skill
in the Word footer.

---

## 8. Section 7 — Provenance Audit

A full table, one row per question. Mandatory columns:

| Column | Example |
|:---|:---|
| response_id | R-00041 |
| question_id | Q-00041 |
| category | Security |
| source | bank_entry:KB-0925 / generated+reviewed |
| tier | HIGH |
| reviewer | jane.doe@example.com |
| review_status | approved |
| last_updated | 2026-04-20T14:22:03Z |

The row count must equal the total question count. Both renderers cross-check
and warn if they differ.

---

## 9. Section 8 — Trend Comparison

Only rendered if historical data exists. One line chart per metric, one
bar-chart comparison for the latest N=5 RFPs:

| Metric | Chart type |
|:---|:---|
| Match rate | Line |
| SME hours saved | Line |
| Turnaround hours | Line |
| Gate rejection count | Bar |

If no prior RFPs in history, this section is replaced with a note:
"Trend data will appear after 2+ RFPs."

---

## 10. Required Charts Summary

| Section | Chart | Type |
|:---|:---|:---|
| 3 | Confidence distribution | Donut |
| 2 | Match rate by category | Stacked bar |
| 4 | Gate outcomes | Icon grid (no chart) |
| 5 | Effort metrics | Single big number + small table |
| 8 | Trend | Line (×3) + bar (×1) |

---

## 11. Word Template Structure

| Page | Contents |
|:---|:---|
| 1 | Cover — title, buyer, RFP ID, submission date, logo |
| 2 | Exec summary |
| 3 | Match rate breakdown (bar + by-category table) |
| 4 | Confidence donut + gate outcomes |
| 5 | Effort metrics + learning-loop stats |
| 6+ | Provenance audit (multi-page table) |
| last | Trend comparison (if available) |

---

## 12. PowerPoint Template Structure

| Slide | Contents |
|:---|:---|
| 1 | Cover (title + logo) |
| 2 | Exec summary — 6 KPIs |
| 3 | Match rate (bar + by-category) |
| 4 | Confidence donut |
| 5 | Gate outcomes (icons + timestamps) |
| 6 | Effort metrics (big numbers) |
| 7 | Learning-loop stats |
| 8 | Trend comparison (if available) |
| 9 | Appendix — link to full provenance audit in Word |

Note: the provenance audit is too large for slides, so the pptx version links
to the Word version rather than duplicating it.

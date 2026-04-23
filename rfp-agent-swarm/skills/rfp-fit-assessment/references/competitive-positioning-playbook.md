# Competitive Positioning Playbook

Used when scoring the Competitive Positioning dimension (weight 10) and
when writing the "Risks & Mitigations" section of the Go/No-Go memo. Also
informs win-theme language that later surfaces in `rfp-respond` drafts.

---

## 1. Inferring the Incumbent

Scan the intaked RFP text for these signals. Enterprise Search can
retrieve prior deal notes with the same buyer to confirm.

| Signal in RFP text | Implication |
|---|---|
| Feature requirements exactly matching a specific competitor's datasheet | That competitor is likely incumbent OR has co-authored the spec |
| References to proprietary APIs / data-model names (e.g. "Object X shall be exportable in Vendor-specific format") | Strong incumbent presence |
| Migration / "import from [vendor]" requirement | Incumbent identified explicitly |
| "Maintain continuity with existing provider" | Incumbent renewal framed as default |
| Unusually short transition timeline | Protects incumbent |
| Pricing model demand matches one vendor's list (e.g. per-MAU) | Spec written to that vendor |

Action: Record inferred incumbent in `working/scorecard.json` under
`competitive.incumbent_inferred`. Enterprise Search the buyer name + the
inferred vendor for public mentions, prior partnerships, or case studies.

---

## 2. Inferring the Shortlist

| Signal | Implication |
|---|---|
| Number of required reference customers unusually high (>=5) | Buyer plans extensive due diligence; shortlist will be narrow |
| "Gartner Magic Quadrant Leader" required | Filters to 3-5 named vendors |
| Industry-specific certification required | Filters to that vertical's vendors |
| Regional presence requirement | Filters by geography |
| Named partner ecosystem integration demanded | Filters to that partner's alliance list |

Cross-reference our CRM and prior RFP outcomes via Enterprise Search.

---

## 3. Typical Competitor Set (placeholder — customise per product line)

| Competitor | Typical strength | Typical weakness | Our differentiator |
|---|---|---|---|
| [COMPETITOR_A] | Brand, breadth | Slow innovation, high TCO | Faster deployment, modern UX |
| [COMPETITOR_B] | Low price | Support quality, scalability | Enterprise-grade SLAs |
| [COMPETITOR_C] | Vertical depth | Narrow outside that vertical | Platform breadth |
| [COMPETITOR_D] | Open-source community | Enterprise features gated | Full enterprise stack included |
| [INCUMBENT_DEFAULT] | Entrenchment, data gravity | Innovation fatigue, cost creep | Migration toolkit, modern arch |

Update this table per sales season; treat as living intel.

---

## 4. Win-Theme Mapping

When the buyer emphasises X in their RFP, lead with Y in our response.
These themes appear in the memo's "Key Evidence" and later in
`rfp-respond` answer framing.

| Buyer emphasis (RFP signal) | Our lead win-theme |
|---|---|
| Time-to-value, rapid onboarding | Deployment speed case studies; reference customer X |
| Cost containment, TCO | 3-year TCO comparison; bundled support |
| Security, compliance | SOC2, ISO27001, named certs; dedicated security review |
| Integration with existing stack | Partner ecosystem; pre-built connectors |
| Scalability, global footprint | Multi-region architecture; largest deployed customer |
| Innovation, roadmap | Public roadmap; R&D investment ratio |
| Service quality | Named CSM model; response-time SLAs |
| Reference customers in vertical | Curated vertical case studies |

---

## 5. Risks of Pursuing When a Competitor is Favoured

Score Competitive Positioning 0-1 and default to No-Go IF two or more of
these hold:

- Incumbent has been deployed >3 years with multi-year auto-renewal.
- RFP spec matches a competitor datasheet verbatim in >=3 places.
- Buyer has publicly named a "preferred partner" overlap with competitor.
- The economic buyer has a prior working relationship with competitor.
- Shortlist publicly announced and we are not on it.

Even with a high overall score, one of these firing is a signal to
escalate to VP Sales before memo sign-off.

---

## 6. Enrichment via Built-In Skills

Use these BEFORE finalising the competitive score. Do NOT call them from
scripts — do it from the agent loop and paste findings into
`working/scorecard.json.competitive.evidence`.

| Built-in | Query pattern | What to extract |
|---|---|---|
| Enterprise Search | `buyer_name AND rfp AND outcome` | Prior deal notes, prior incumbent, prior win/loss |
| Enterprise Search | `buyer_name AND competitor_name` | Known partnership or prior loss |
| Deep Research | `buyer_name press releases last 12 months` | Strategic moves, tech announcements |
| Deep Research | `buyer_name + [incumbent vendor]` | Public case studies, partnership depth |
| Deep Research | Industry analyst report on buyer vertical | Vendor positioning |

Budget: 15-20 minutes of enrichment per RFP. More than that is a signal
to push to the AE or Competitive Intel team.

---

## 7. Sensitivity Flags to Set on the Memo

When competitive analysis surfaces these, note them as bullets in the
memo's `Risks & Mitigations` section verbatim:

- "Incumbent fatigue signals — confirm with AE before committing effort"
- "Spec mirrors competitor X datasheet — pursue differentiated win-theme"
- "Buyer analyst relationships may favour vendor Y — references required"
- "Regional delivery partner not confirmed — escalate to Alliances"

---

## 8. Anti-Patterns

Avoid these during competitive scoring:

- Confirmation bias toward a known incumbent when evidence is ambiguous.
- Over-weighting a single buyer-stakeholder preference signal.
- Assuming a public case study = current preference (may be stale).
- Scoring 0 without written evidence that the RFP was written to a spec.
- Scoring 5 in the absence of any competitive intel (score 3 = default).

If no credible intel is available, default the dimension to raw=3 and
mark `confidence: LOW` in the scorecard notes.

---

## 9. Post-Decision Feedback Loop

After submission, regardless of outcome, capture:

- Confirmed shortlist (win or loss notification).
- Winning vendor (if not us).
- Price delta (if disclosed).
- Buyer feedback on our positioning.

Feed these back into `rfp-answer-bank` (as metadata) and into the next
quarterly refresh of the Competitor Set table above.

# Branding Guide

All values below are **placeholders**. The organisation fills them in via
`branding.tokens.json` (one file per tenant), which the skill reads at
runtime. Do not hard-code any value.

---

## 1. Typography

| Role | Token | Default placeholder |
|:---|:---|:---|
| Primary font (body) | `font.body` | `[PRIMARY_FONT]` (e.g. "Inter") |
| Secondary font (headings) | `font.heading` | `[HEADING_FONT]` (e.g. "Source Serif") |
| Monospaced (code / tables) | `font.mono` | `[MONO_FONT]` (e.g. "JetBrains Mono") |

### Heading scale

| Level | Size (pt) | Weight |
|:---|:---:|:---|
| H1 | 24 | 700 |
| H2 | 18 | 600 |
| H3 | 14 | 600 |
| H4 | 12 | 600 |
| Body | 11 | 400 |
| Caption | 9 | 400 |

Line height: 1.4 for body, 1.2 for headings.

---

## 2. Colour Palette

| Role | Token | Placeholder hex | Notes |
|:---|:---|:---|:---|
| Primary | `colour.primary` | `[#000000]` | Headings, bold accents |
| Secondary | `colour.secondary` | `[#333333]` | Sub-headings, borders |
| Accent | `colour.accent` | `[#0066CC]` | Links, callouts, chart primary |
| Neutral | `colour.neutral` | `[#F2F2F2]` | Table banding, backgrounds |
| Success | `colour.success` | `[#2E7D32]` | Gate passes, HIGH confidence |
| Warning | `colour.warning` | `[#F9A825]` | MEDIUM confidence |
| Danger | `colour.danger` | `[#C62828]` | Gate rejections, LOW confidence |
| Text on light | `colour.text.light` | `[#111111]` | Body text on light backgrounds |
| Text on dark | `colour.text.dark` | `[#FFFFFF]` | Body text on dark backgrounds |

All placeholder hex codes are examples — the organisation sets the real values
in `branding.tokens.json`.

---

## 3. Logo Placement Rules

| Placement | Rule |
|:---|:---|
| Cover page | Centred; 25% of page width; 40 mm top margin |
| Page header (Word, PDF) | Top-left; 18 mm tall; repeated on every page |
| Page footer | None (footer reserved for legal text) |
| Analytics report | Top-left of cover slide and each section divider |
| Cover letter | Top-right of letterhead |

Logo file formats accepted: SVG preferred, PNG (with transparency) fallback.
`branding.tokens.json` points at the logo file path.

---

## 4. Footer Text

Every page of the final PDF carries the disclaimer footer (see
`/mnt/user-config/.claude/skills/rfp-assemble/assets/disclaimer-footer.md`).

| Field | Token |
|:---|:---|
| Company legal name | `company.legal_name` |
| Registration number | `company.registration` |
| Confidentiality marker | `document.confidentiality` (e.g. "Confidential") |
| Submission date | `rfp.submission_date` |
| Page number | Auto-generated per renderer |

---

## 5. Accessibility

| Requirement | Target |
|:---|:---|
| Contrast ratio (body text) | ≥ 4.5 : 1 (WCAG AA) |
| Contrast ratio (large text) | ≥ 3 : 1 |
| Alt text on figures | Required for every non-decorative image |
| Alt text on charts (analytics) | Required; include key numbers in the alt text |
| Table headers | First row marked as header in Word and Excel |
| Reading order | Must match visual order (renderer default is fine) |
| Hyperlink text | Descriptive — never "click here" |

If a colour pair in the palette fails contrast, the renderer falls back to the
nearest accessible pair and logs a warning in the manifest.

---

## 6. Component-Level Guidance

| Component | Rule |
|:---|:---|
| Tables | Header row in `colour.primary` with white text; alternating `colour.neutral` banding |
| Callouts | Left border 4 mm wide in `colour.accent` |
| Confidence badges | HIGH = `colour.success`, MEDIUM = `colour.warning`, LOW = `colour.danger` |
| Charts (analytics) | Primary series in `colour.accent`; secondary in `colour.secondary` |
| Cover letter | No tables, no charts — plain formal letter |

---

## 7. Branding Token File

The organisation supplies a JSON file, typically at
`working/branding.tokens.json`. Example structure:

```
{
  "font": { "body": "Inter", "heading": "Source Serif", "mono": "JetBrains Mono" },
  "colour": {
    "primary": "#0A1F44", "secondary": "#3C4F6B", "accent": "#0066CC",
    "neutral": "#F2F2F2", "success": "#2E7D32", "warning": "#F9A825",
    "danger": "#C62828",
    "text": { "light": "#111111", "dark": "#FFFFFF" }
  },
  "logo": { "path": "assets/brand/logo.svg" },
  "company": {
    "legal_name": "Example Corp Ltd.",
    "registration": "12345678"
  },
  "document": { "confidentiality": "Confidential" }
}
```

`assemble_document.py` reads this file and copies the resolved values into the
manifest's `style` block so downstream renderers do not need to re-read it.

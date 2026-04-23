# Quality Rubric

Scoring rubric for newly authored skill packages. Every skill produced by `skill-factory` should score ≥75/100 before being reported as complete.

---

## Scoring Dimensions (25 points each)

### 1. Discoverability (0–25)

How reliably will the skill be auto-invoked for the right user requests?

| Criterion | Points |
|-----------|--------|
| ≥8 trigger phrases in description | 8 |
| Each trigger phrase quoted as user language (not internal jargon) | 6 |
| "Do NOT use for…" exclusion clause present | 5 |
| Trigger phrases cover synonyms and natural variations | 3 |
| Name is kebab-case, semantic, not shadowing built-ins | 3 |

### 2. Completeness (0–25)

Does the skill contain everything needed to execute the workflow?

| Criterion | Points |
|-----------|--------|
| All 10 mandatory SKILL.md sections present | 8 |
| Quick Start shows a concrete example (named user, named entities) | 5 |
| Core Instructions include at least one table, template, or framework | 5 |
| Output Deliverables table maps each output to a file skill | 4 |
| Built-In Skills Used table is accurate (no fabricated built-ins) | 3 |

### 3. Rigor (0–25)

Is the skill's logic sound, cited, and free of hallucination?

| Criterion | Points |
|-----------|--------|
| Any cited framework is a real/established one (ADKAR, Kotter, RACI, etc.) | 8 |
| No fabricated citations, statistics, or URLs | 6 |
| Calculations delegated to code tools, never mental arithmetic | 5 |
| Verification gate present ("Before reporting success…") | 3 |
| Guardrails include ≥5 hard rules | 3 |

### 4. Maintainability (0–25)

Is the skill easy to audit, extend, and safely modify later?

| Criterion | Points |
|-----------|--------|
| ≥5 tables in SKILL.md | 6 |
| ≥6 rows in Common Issues troubleshooting table | 6 |
| Every `references/*.md`, `scripts/*.py`, `assets/*.md` is cross-linked from SKILL.md | 5 |
| SKILL.md is 200–400 lines (not bloated, not thin) | 4 |
| File naming follows conventions (kebab-case md, snake_case py) | 4 |

---

## Score Bands

| Score | Band | Action |
|-------|------|--------|
| 90–100 | Excellent | Ship |
| 75–89 | Good | Ship, note top improvement for next iteration |
| 50–74 | Needs work | Fix lowest-scoring dimension before shipping |
| 0–49 | Unshippable | Rewrite from template |

---

## Self-Check Script (Manual)

Before declaring a skill complete, walk through:

1. Open SKILL.md; count trigger phrases in description → must be ≥8
2. Verify each listed built-in skill is a real one (check `/opt/workspace-config/.claude/skills/`)
3. Search for citations; verify each framework is real (via web_search or deep-research if unsure)
4. Grep the SKILL.md for `references/`, `scripts/`, `assets/` — every path referenced must exist; every file that exists must be referenced
5. Check line count: `wc -l SKILL.md` → 200–400
6. Count tables and troubleshooting rows

If any check fails, fix before proceeding to the next skill in the batch.

---

## Anti-Patterns to Avoid

| Anti-pattern | Why it's bad | Fix |
|--------------|--------------|-----|
| Description with 3 generic triggers ("help me with X") | Won't auto-invoke reliably | Expand to ≥8 specific user-quoted phrases |
| Fabricated framework name | Misleads the user, breaks trust | Only cite established frameworks, or omit |
| "This skill will calculate totals…" with no code tool call | Mental arithmetic is unreliable | Route every calculation through a script or code tool |
| Reference file with no inbound link from SKILL.md | Dead weight; never loaded | Link from SKILL.md or delete the file |
| Script with `pip install` or third-party import | Will fail at runtime | Refactor to stdlib only |
| SKILL.md >400 lines with inline lookup tables | Bloats context on every invocation | Move tables to `references/*.md` |
| Identical trigger phrases to an existing skill | Ambiguous routing | Differentiate scope or merge skills |

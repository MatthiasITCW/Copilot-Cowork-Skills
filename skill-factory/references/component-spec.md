# Component Specification

Exact sizing, content, and placement rules for every component of a skill package.

---

## SKILL.md

**Location**: `/mnt/user-config/.claude/skills/{name}/SKILL.md` (required, one per skill)

**Size**: 200–400 lines of Markdown. Below 200 lines suggests missing detail; above 400 suggests content should be split into `references/`.

**Structure (mandatory order)**:

| # | Section | Required | Notes |
|---|---------|----------|-------|
| 1 | YAML frontmatter | Yes | `name`, multi-line `description`, optional `cowork:` |
| 2 | H1 title | Yes | Human-readable name |
| 3 | When to Use | Yes | Bullet list — concrete situations |
| 4 | When NOT to Use | Yes | Bullet list — delegation to other skills |
| 5 | Quick Start | Yes | One example workflow, 5–10 numbered steps |
| 6 | Core Instructions | Yes | Main body — use tables, templates, frameworks |
| 7 | Built-In Skills Used | Yes | Table mapping skill → usage |
| 8 | Output Deliverables | Yes | Table mapping deliverable → file skill |
| 9 | Guardrails | Yes | Hard rules as bullets |
| 10 | Common Issues | Yes | ≥6-row troubleshooting table |

**Frontmatter schema**:

```yaml
---
name: skill-name                    # Must match directory; kebab-case; regex ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$
description: |                      # Multi-line block; ≥8 trigger phrases; "Do NOT use for" exclusions
  One-paragraph summary of what the skill does.
  Use when user asks to "trigger 1", "trigger 2", ..., "trigger 8+".
  Do NOT use for [X] — use [other skill] instead.
cowork:                             # Optional UI metadata
  category: productivity            # productivity|communication|analysis|writing|research|automation|custom
  icon: puzzle-piece                # calendar|mail|document|chart|lightning|search|clock|users|star|puzzle-piece
---
```

---

## references/ folder

**Purpose**: Dense lookup tables, scoring algorithms, classification frameworks, heuristics that would bloat SKILL.md.

**Size**: 80–200 lines per file.

**When to include**:
- Scoring rubrics with many dimensions
- Classification frameworks with lookup tables
- Jurisdiction/region-specific reference data
- Multi-scenario heuristics or decision trees

**Naming**: kebab-case, descriptive: `quality-rubric.md`, `scoring-matrix.md`, `jurisdiction-sources.md`.

**Cross-linking**: Every reference file MUST be linked from SKILL.md at least once, e.g.:

```markdown
See [references/quality-rubric.md](references/quality-rubric.md) for the full scoring breakdown.
```

A reference file with no inbound link is dead weight — either link it or delete it.

---

## scripts/ folder

**Purpose**: Deterministic processing that should run as code, not AI.

**Size**: 150–400 lines per file.

**When to include**:
- Text segmentation (contract clauses, transcript speakers)
- Data extraction from structured input
- Formula recalculation or validation
- Scoring engines with fixed algorithms
- Aggregation / statistical computation

**Constraints**:
- Pure Python 3
- Standard library only — no `pip install`, no external packages
- Structured JSON output to stdout
- Non-zero exit on error; stderr for human-readable error message
- Idempotent — safe to re-run on the same input

**Invocation pattern from SKILL.md**:

```bash
python scripts/segment_contract.py <input_path> --output working/segmented.json
```

**Cross-linking**: Every script must be referenced in at least one workflow step.

---

## assets/ folder

**Purpose**: Static templates and pre-approved content inserted verbatim at runtime — never AI-generated.

**Size**: 10–150 lines per file.

**When to include**:
- Boilerplate clauses (legal, compliance, privacy)
- Pre-approved email/cover-note templates
- Standard disclaimers or privilege notices
- Fixed checklists that run at the start or end of a workflow

**Placeholder syntax**: Use `[PLACEHOLDER_NAME]` for runtime substitution, e.g. `[CUSTOMER_NAME]`, `[EFFECTIVE_DATE]`, `[JURISDICTION]`.

**Constraints**:
- Content must be stable across invocations
- No conditional logic — if variation is needed, split into multiple asset files
- Pre-reviewed by a subject-matter expert where relevant (legal, compliance)

**Cross-linking**: Same rule — every asset must be linked from SKILL.md.

---

## Filename Conventions

| Component | Pattern | Example |
|-----------|---------|---------|
| SKILL.md | Exact name, all caps `.md` | `SKILL.md` |
| references | kebab-case, descriptive | `scoring-rubric.md`, `jurisdiction-sources.md` |
| scripts | snake_case, verb_noun | `segment_contract.py`, `compute_score.py` |
| assets | kebab-case, descriptive | `cover-note-template.md`, `privilege-notice.md` |

---

## Size Summary

| Component | Min lines | Max lines | Blocking? |
|-----------|-----------|-----------|-----------|
| SKILL.md | 200 | 400 | Warning at <200, hard block at >1 MB |
| reference file | 80 | 200 | Advisory only |
| script file | 150 | 400 | Advisory only |
| asset file | 10 | 150 | Advisory only |

If a reference exceeds 200 lines, consider splitting into multiple files. If a script exceeds 400 lines, consider breaking into modules (though stdlib-only constraint means no package installation).

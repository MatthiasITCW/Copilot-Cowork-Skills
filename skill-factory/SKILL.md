---
name: skill-factory
description: |
  Batch-creates complete custom Cowork skill packages (SKILL.md plus optional
  references/, scripts/, assets/ folders) by first studying built-in skills as
  templates, then generating skills at a specified tier (Standard, Enhanced,
  Full Package) with rigorous quality controls, trigger-phrase density,
  cross-linked supporting files, and post-write verification.
  Use when the user asks to "create skills", "build a skill package",
  "generate custom skills", "make multiple skills", "bulk create skills",
  "spin up a skill package", "build a full skill", "create a tiered skill",
  "author a skill with references and scripts", "create skills in OneDrive",
  "skill factory", "batch skill creation", or describes a multi-skill
  authoring workflow with a quality bar.
  Do NOT use for single quick skill creation without supporting files — use
  the built-in `skills` skill for that. Do NOT use for editing, deleting, or
  auditing existing skills — use `skills` for lifecycle operations.
cowork:
  category: automation
  icon: puzzle-piece
---

# Skill Factory

Batch-author complete custom Cowork skill packages — SKILL.md plus optional `references/`, `scripts/`, and `assets/` folders — to a rigorous quality bar, with pre-write template study, tiered structure selection, and post-write verification.

## When to Use

- User wants to create **one or more** new custom skills with supporting files
- User specifies a tier (Standard, Enhanced, Full Package) or needs guidance picking one
- User asks for a "skill package" with references, scripts, or assets
- User provides a batch list of skills to generate in a single request
- User wants skills authored against an explicit quality bar (trigger phrases, tables, troubleshooting rows)

## When NOT to Use

- Simple single-skill creation with no supporting files → use the built-in `skills` skill
- Editing or tuning an existing skill → use `skills`
- Deleting or auditing existing skills → use `skills`
- Editing personal instructions (`copilot-instructions.md`) → use `skills`
- Writing non-skill documents (Word, PDF, Excel) → use the corresponding document skill

---

## Quick Start

**User**: "Create 3 full-package skills: project-retrospective, executive-brief, quarterly-planning."

**Steps**:
1. **Study templates** — read 3–4 built-in skills at `/opt/workspace-config/.claude/skills/` and the `legal-redliner` gold-standard at `/mnt/user-config/.claude/skills/legal-redliner/`
2. **Check capacity** — confirm new skills fit under the 50-skill limit
3. **Validate names** — ensure kebab-case, no shadowing of built-in names
4. **Draft each package** — SKILL.md first, then references/scripts/assets per tier
5. **Write files** — `mkdir -p` the skill directory, then Write each file
6. **Verify** — `Glob` the skill directory and confirm every declared file exists
7. **Report** — tell the user what was created and that OneDrive sync lands in ~35 seconds

---

## Paths & Sync

| Path | Purpose | Writable |
|------|---------|----------|
| `/mnt/user-config/.claude/skills/{name}/` | Personal skill directory — **write here** | Yes, syncs to OneDrive |
| `/opt/workspace-config/.claude/skills/` | Built-in skills — **study only** | Read-only |
| `/mnt/user-config/.claude/skills/legal-redliner/` | Gold-standard full-package example | Read-only reference |

**OneDrive visibility**: Files written to `/mnt/user-config/.claude/skills/{name}/` appear in the user's OneDrive under `Cowork/Skills/{name}/` after ~35 seconds (rclone flush + blob replication).

**Limit**: 50 skills maximum. Each `SKILL.md` must stay under 1 MB.

---

## Tier Selection

| Tier | Folders | When to Use |
|------|---------|-------------|
| **Standard** | `SKILL.md` only | Simple workflows, narrow domain, no lookup tables or static templates required |
| **Enhanced** | `SKILL.md` + `references/` | Dense lookup tables, scoring rubrics, classification frameworks, or heuristics that would bloat SKILL.md |
| **Full Package** | `SKILL.md` + `references/` + `scripts/` + `assets/` | Deterministic processing (segmentation, scoring engines), pre-approved boilerplate, or complex multi-step pipelines (e.g., legal-redliner) |

If the user does not specify a tier, propose one based on scope — recommend Enhanced for any skill needing frameworks like ADKAR/RACI/RAID, and Full Package when the skill has deterministic computation or verbatim template content.

See [references/component-spec.md](references/component-spec.md) for exact sizing rules per component.

---

## Authoring Workflow

### Phase 1 — Study (MANDATORY before writing)

Before drafting anything, read these references to absorb the house style:

1. **3–4 built-in skills** at `/opt/workspace-config/.claude/skills/` — e.g. `calendar-management/SKILL.md`, `daily-briefing/SKILL.md`, `meeting-intel/SKILL.md`, `stakeholder-comms/SKILL.md`
2. **Legal-redliner** at `/mnt/user-config/.claude/skills/legal-redliner/` — the gold-standard Full Package with references, scripts, and assets all cross-linked
3. **Templates** at `/opt/workspace-config/.claude/skills/skills/references/templates.md`

Extract and mirror:
- YAML frontmatter shape (`name`, multi-line `description`, optional `cowork:` block)
- Section ordering (Overview/When to Use/When NOT/Quick Start/Core Instructions/Guardrails/Common Issues)
- Table patterns, trigger-phrase density, tone

### Phase 2 — Plan Each Skill

For every skill in the batch, capture:

| Field | Requirement |
|-------|-------------|
| Name | kebab-case, `^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$`, not shadowing built-ins |
| One-line description | Outcome-oriented, business language |
| Tier | Standard / Enhanced / Full Package |
| Trigger phrases | ≥8, phrased as user-quoted actions |
| Frameworks used | ADKAR, 5 Whys, RACI, RAID, Kotter, OKR, etc. (real, established) |
| Built-in skills leveraged | docx, xlsx, pptx, pdf, render-ui, email, calendar, etc. |
| Output deliverables | Each mapped to a specific file skill |

### Phase 3 — Draft SKILL.md

Every SKILL.md must contain these sections in order:

1. **YAML frontmatter** — `name`, multi-line `description` with all triggers plus "Do NOT use for…" exclusions, optional `cowork:` block
2. **H1 title** matching the skill's human name
3. **When to Use** — bullet list of concrete trigger situations
4. **When NOT to Use** — bullet list with delegation to other skills
5. **Quick Start** — one example end-to-end workflow
6. **Core Instructions / Workflow** — detailed steps with tables, templates, or frameworks
7. **Built-In Skills Used** — table mapping each built-in skill to how it's used
8. **Output Deliverables** — table mapping each deliverable to a file skill (docx/xlsx/pptx/pdf) or inline render
9. **Guardrails** — hard rules as bullet list
10. **Common Issues** — troubleshooting table with ≥6 rows

Target 200–400 lines of Markdown. See [references/quality-rubric.md](references/quality-rubric.md) for scoring.

### Phase 4 — Author Supporting Files (Enhanced / Full Package)

Only for tiers that include them — skip for Standard.

**references/** (Enhanced and above)
- Dense lookup tables, scoring algorithms, classification frameworks, heuristics
- 80–200 lines per file
- Loaded on-demand by the skill
- Link from SKILL.md with `[name](references/file.md)` using relative paths

**scripts/** (Full Package only)
- Pure Python 3, standard library only
- Deterministic processing that should run as code, not AI (text segmentation, data extraction, scoring engines)
- Structured JSON output to stdout
- 150–400 lines per file
- Reference from SKILL.md via `python scripts/filename.py <args>`

**assets/** (Full Package only)
- Static templates and pre-approved content inserted verbatim at runtime
- Never AI-generated at runtime — stored literal content only
- Use `[PLACEHOLDER_NAME]` syntax for variable substitution
- 10–150 lines per file
- Link from SKILL.md with `[name](assets/file.md)`

See [assets/cover-note-template.md](assets/cover-note-template.md) for a ready-to-reuse cover-note template and [assets/checklist-template.md](assets/checklist-template.md) for a pre-write QA checklist.

### Phase 5 — Write

For each skill in the batch:

```bash
mkdir -p /mnt/user-config/.claude/skills/{name}/references /mnt/user-config/.claude/skills/{name}/scripts /mnt/user-config/.claude/skills/{name}/assets
```

(Omit subfolders that aren't required for the tier.)

Use the **Write tool** — not `echo` or `cat` heredocs — to create each file. Writes must be idempotent: if re-running the batch, confirm before overwriting.

### Phase 6 — Verify (DELIVERY GATE)

After writing, for every skill in the batch:

```
Glob /mnt/user-config/.claude/skills/{name}/**/*
```

Confirm:
- [ ] SKILL.md present
- [ ] Every `references/*.md` declared in SKILL.md exists
- [ ] Every `scripts/*.py` referenced exists
- [ ] Every `assets/*.md` referenced exists
- [ ] No broken relative links in SKILL.md

If any file is missing, investigate and re-write before reporting success. Never tell the user "done" before `Glob` confirms the files.

### Phase 7 — Report

Tell the user in plain language:
- What was created (bulleted list with name + one-line description + tier)
- OneDrive sync timing (~35 seconds)
- How to test (invoke with a trigger phrase from the description)

---

## Quality Bar

Every skill produced by this factory must meet these thresholds:

| Metric | Minimum |
|--------|---------|
| SKILL.md length | 200 lines |
| SKILL.md length (max) | 400 lines |
| Trigger phrases in description | 8 |
| Tables in SKILL.md | 5 |
| Troubleshooting rows | 6 |
| Frameworks cited (if analytical) | 1+ real/established framework |
| Cross-links from SKILL.md to supporting files | Every reference/script/asset must be linked |
| Calculations performed by AI | 0 — all calculations must use code tools |

See [references/quality-rubric.md](references/quality-rubric.md) for the full scoring breakdown.

---

## Built-In Skills Used

| Built-in Skill | How It's Used |
|---------------|---------------|
| **skills** | Name validation, count checks, and delegation for single-skill lifecycle ops |
| **Word (docx)** | Skills often declare docx deliverables — this factory verifies the mapping is correct |
| **Excel (xlsx)** | Same — checks the skill's output table points to xlsx where tabular data is produced |
| **PowerPoint (pptx)** | Same — verifies deck deliverables reference pptx |
| **PDF** | Same — verifies PDF deliverables route through the pdf skill |
| **render-ui** | Recommended for skills with KPI cards, charts, or 4+ row tables |
| **Enterprise Search** | For skills that retrieve M365 content — verifies the retrieval pattern is documented |
| **Deep Research** | For skills with verifiable claims — verifies the delegation is declared |

---

## Output Format

| Deliverable | Location | File Skill |
|-------------|----------|-----------|
| Skill package (SKILL.md + supporting files) | `/mnt/user-config/.claude/skills/{name}/` | Plain Markdown + Python (written via Write tool) |
| Batch summary | Inline chat response | None — plain text |
| Verification report | Inline chat response | None — plain text |

This factory does **not** produce docx/xlsx/pptx/pdf — it produces Markdown + Python source files for the skill runtime.

---

## Guardrails

- **Never modify built-in skills**: `/opt/workspace-config/.claude/skills/` is read-only
- **Never fabricate frameworks**: Only cite established frameworks (ADKAR, Kotter, 5 Whys, RACI, RAID, OKR, MoSCoW, SWOT, PESTLE, etc.) — if unsure, omit or use deep-research to verify
- **Always study templates first**: Never write a skill without reading at least 3 built-in skills in the current session
- **Verify before reporting success**: Glob the output directory after writing — missing files must block the success message
- **Kebab-case names only**: `^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$`, no shadowing of built-ins (pdf, docx, xlsx, pptx, skills, calendar-management, meeting-intel, stakeholder-comms, daily-briefing, schedule-meeting, deep-reasoning, render-ui)
- **Respect the 50-skill limit**: Count existing skills before creating; if the batch would exceed the limit, inform the user and ask what to remove
- **All calculations via code**: Any scoring, counting, or percentage in a generated skill must route to code tools — never instruct the AI to do mental arithmetic
- **Cross-link every file**: If `references/foo.md` exists but SKILL.md doesn't link to it, it is dead weight — either link or delete
- **Plain language in descriptions**: Use outcome-oriented trigger phrases ("summarize my week") not implementation details ("calls SearchM365 with keyword filter")

---

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Skill not triggering after creation | Description lacks trigger phrases or replication lag | Confirm ≥8 trigger phrases present; wait 35s; test with exact trigger from description |
| YAML parse error on load | Unescaped colon in description or bad indentation | Wrap description in `|` block scalar; indent consistently with 2 spaces |
| Skill name rejected | Invalid characters, starts with non-alphanumeric, or shadows a built-in | Regenerate as kebab-case, ensure first char is letter/digit, avoid built-in names |
| Supporting files exist but skill never uses them | Missing cross-links in SKILL.md | Add `[label](references/foo.md)` or `python scripts/foo.py` references |
| Write succeeds but Glob shows empty directory | Wrote to wrong path (e.g., `/mnt/workspace/` instead of `/mnt/user-config/`) | Re-write to `/mnt/user-config/.claude/skills/{name}/` and re-verify |
| Batch hits the 50-skill cap | Too many existing skills | List current skills, have user pick what to delete before continuing |
| Script in skill fails at runtime | Non-stdlib import or wrong Python path | Restrict to Python 3 standard library; test execution path before committing |
| Skill description too broad, triggers on unrelated requests | Overly generic language | Add "Do NOT use for…" exclusions and narrow the trigger verbs |
| SKILL.md exceeds 400 lines | Too much content inline | Move dense tables/frameworks to `references/*.md` and cross-link |
| Generated skill has no troubleshooting table | Draft phase skipped Common Issues | Always include ≥6 rows — use [assets/checklist-template.md](assets/checklist-template.md) as a pre-write checklist |

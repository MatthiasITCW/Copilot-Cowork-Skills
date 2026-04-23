# Pre-Write QA Checklist

Run this checklist **before** writing each SKILL.md to disk. Every unchecked item must be resolved or explicitly accepted.

---

## Frontmatter

- [ ] `name` matches the intended directory name exactly
- [ ] `name` is kebab-case, starts with letter/digit, ≤64 chars
- [ ] `name` does not shadow a built-in (pdf, docx, xlsx, pptx, skills, calendar-management, meeting-intel, stakeholder-comms, daily-briefing, schedule-meeting, deep-reasoning, render-ui)
- [ ] `description` uses `|` block scalar for multi-line
- [ ] `description` contains ≥8 distinct trigger phrases in quotes
- [ ] `description` contains at least one "Do NOT use for…" exclusion
- [ ] Optional `cowork:` block has valid `category` and `icon`

## Structure

- [ ] H1 title present immediately after frontmatter
- [ ] When to Use section with ≥3 bullets
- [ ] When NOT to Use section with ≥2 bullets, each delegating to a named skill
- [ ] Quick Start shows one concrete example (named user, named entities)
- [ ] Core Instructions / Workflow has at least one table or framework
- [ ] Built-In Skills Used table — every row references a real built-in
- [ ] Output Deliverables table — every row maps to a file skill (docx/xlsx/pptx/pdf) or "inline"
- [ ] Guardrails section with ≥5 hard rules
- [ ] Common Issues table with ≥6 rows

## Content

- [ ] Every cited framework is a real, established one (ADKAR, Kotter, 5 Whys, RACI, RAID, OKR, MoSCoW, SWOT, PESTLE, Pyramid Principle, STAR, 4Ls, Start-Stop-Continue, Fishbone, Eisenhower Matrix, etc.)
- [ ] No fabricated statistics, citations, or URLs
- [ ] Any calculation the skill performs is routed through a code tool, not mental arithmetic
- [ ] Tone uses plain business language, not internal jargon
- [ ] Trigger phrases are phrased as the user would say them, not as tool descriptions

## Cross-Links

- [ ] Every `references/*.md` file created is linked from SKILL.md
- [ ] Every `scripts/*.py` file created is referenced in at least one workflow step
- [ ] Every `assets/*.md` file created is linked from SKILL.md
- [ ] Every `[link](path)` in SKILL.md points to a file that will exist after write
- [ ] Relative paths used (not absolute) for all supporting-file links

## Sizing

- [ ] SKILL.md is 200–400 lines
- [ ] Reference files are 80–200 lines each
- [ ] Scripts are 150–400 lines each
- [ ] Asset files are 10–150 lines each

## Tier Consistency

- [ ] Standard tier: only SKILL.md, no supporting folders
- [ ] Enhanced tier: SKILL.md + references/ only
- [ ] Full Package tier: SKILL.md + references/ + scripts/ + assets/, all populated

---

## Post-Write Verification

After writing, confirm:

- [ ] `Glob /mnt/user-config/.claude/skills/{name}/**/*` lists every expected file
- [ ] No extra unexpected files present
- [ ] Directory count under 50 total personal skills
- [ ] User informed of the ~35s OneDrive replication delay

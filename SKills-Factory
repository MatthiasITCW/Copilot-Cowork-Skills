Create a custom Cowork skill called skill-factory in my personal skill library. This will be a meta-skill that knows how to create other skills for me on demand.

Before writing anything, gather current guidance from these sources in this order:

Official source of truth (fetch live) — https://learn.microsoft.com/en-us/microsoft-365/copilot/cowork/use-cowork#create-custom-skills. Use web_fetch to pull the current version; do not rely on pre-training knowledge of this page, as it evolves. Extract any current rules on skill limits, naming, frontmatter schema, folder structure, and file size caps.
Cowork skill authoring docs (fetch live) — search learn.microsoft.com for the latest pages on "Cowork custom skills", "SKILL.md frontmatter", and "personal skills OneDrive" and fetch whichever are most current. If any rule conflicts with step 3 below, the official docs win.
In-product examples (read local) — study 3–4 built-in skills at 
/opt/workspace-config/.claude/skills/
 (e.g. calendar-management, daily-briefing, meeting-intel, stakeholder-comms) for section ordering and trigger-phrase density, and read 
/mnt/user-config/.claude/skills/legal-redliner/
 as the gold-standard Full Package example (SKILL.md + references/ + scripts/ + assets/). Also read 

templates.md
 for starter templates.
Write the skill package to 
/mnt/user-config/.claude/skills/skill-factory/
 with these files:


SKILL.md
 (200–400 lines) with: YAML frontmatter (name + multi-line description with ≥8 trigger phrases like "create skills", "build a skill package", "batch create skills", "skill factory", plus "Do NOT use for…" exclusions that delegate single-skill lifecycle ops to the built-in skills skill); H1 title; When to Use / When NOT to Use; Quick Start with a concrete end-to-end example; a Tier Selection table (Standard = SKILL.md only, Enhanced = + references/, Full Package = + references/ + scripts/ + assets/); a 7-phase Authoring Workflow that begins with a live fetch of the Microsoft Learn source-of-truth URL above (so every skill-creation run picks up the latest rules) followed by Plan → Draft SKILL.md → Author supporting files → Write → Verify with Glob → Report; a Quality Bar table (≥200 lines SKILL.md, ≥8 trigger phrases, ≥5 tables, ≥6 troubleshooting rows, all calculations via code tools, every reference/script/asset cross-linked); Built-In Skills Used table; Output Format table; Guardrails (always fetch the Microsoft Learn source first, never modify built-ins, never fabricate frameworks, kebab-case names, respect current skill cap from the docs, verify before reporting success); Common Issues troubleshooting table with ≥6 rows.


external-sources.md
 (80–200 lines) — curated list of live URLs the skill should fetch at runtime, with a description, what to extract, and refresh cadence for each. Must include at minimum: the Microsoft Learn use-cowork#create-custom-skills page, the Cowork skill authoring docs, and any linked Adaptive Cards or Microsoft Graph references. Structure as a table with columns Source | URL | What to Extract | Refresh When. Instruct readers to prefer these over cached values.


component-spec.md
 (80–200 lines) — exact sizing rules per component (SKILL.md 200–400 lines with mandatory sections, references 80–200 lines, scripts 150–400 lines Python 3 stdlib only with JSON output, assets 10–150 lines verbatim content with [PLACEHOLDER] syntax), filename conventions, and frontmatter schema. Every numeric limit in this file must note that it is subject to the live Microsoft Learn doc and should be re-verified if the doc was fetched today.


quality-rubric.md
 (80–200 lines) — 100-point scoring rubric across 4 dimensions (Discoverability, Completeness, Rigor, Maintainability — 25 points each), score bands (90+ excellent, 75+ good, <75 needs work), a manual self-check procedure, and an anti-patterns table.


cover-note-template.md
 (10–150 lines) — verbatim completion-report template for reporting batch results back to the user, with [PLACEHOLDER] syntax and a filled example.


checklist-template.md
 (10–150 lines) — pre-write QA checklist covering: "fetched Microsoft Learn source-of-truth within this session" as the first item, then frontmatter validity, mandatory section presence, content rigor (real frameworks only, no fabricated citations), cross-link integrity, sizing, tier consistency, and post-write verification.

Rules:

Live sources beat cached knowledge. Every skill-creation run must fetch the Microsoft Learn source-of-truth page at the start. If the fetch fails, tell the user and fall back to local references with an explicit "verified against docs as of [date]" disclaimer.
All calculations the skill instructs must route through code tools, never mental arithmetic.
Every 

*.md
, 

*.py
, 

*.md
 must be cross-linked from SKILL.md via relative paths.
Use real established frameworks only (ADKAR, Kotter, 5 Whys, RACI, RAID, OKR, MoSCoW, SWOT, PESTLE, Pyramid Principle, etc.).
Kebab-case name, must not shadow built-ins (pdf, docx, xlsx, pptx, skills, calendar-management, etc.).
Respect whatever skill cap is stated in the current Microsoft Learn docs at fetch time.
After writing, run 
*
 to verify all 6 files exist. Do not report success until verification passes. Tell me the files will appear in OneDrive under 
Cowork/Skills/skill-factory/
 within ~35 seconds, and note the date the Microsoft Learn source was last fetched so I know when to refresh.

